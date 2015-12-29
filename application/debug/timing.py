# Copyright (C) 2006-2012 Dan Pascu. See LICENSE for details.
#

"""Measure code execution time for benchmarking and profiling purposes.

Usage:

from application.debug.timing import timer, time_probe, measure_time

with timer(description="statement's description"):
    ...

def foo():
    ...
    with time_probe("foo's critical section"):
        ...
    ...

@measure_time
def foo():
    ...

"""

import dis
import gc
import inspect
import struct
import sys

from collections import deque
from itertools import chain, izip, takewhile
from time import clock, time

from application.python.decorator import decorator, preserve_signature
from application.python.types import MarkerType


__all__ = ["Timer", "TimeProbe", "timer", "time_probe", "measure_time"]


class Automatic(object):
    __metaclass__ = MarkerType


class Autodetect(int):
    def __new__(cls, *args, **kw):
        return int.__new__(cls)

    def __repr__(self):
        return self.__class__.__name__

Autodetect = Autodetect()


class Timer(object):
    def __init__(self, description=None, loops=Autodetect, repeat=3, time_function=Automatic):
        if not isinstance(loops, int):
            raise TypeError("loops should be an integer number")
        if not callable(time_function):
            raise TypeError("time_function should be a callable")
        self.description = description
        self.loops = loops
        self.repeat = repeat
        if time_function is Automatic:
            self.time_function = clock if sys.platform == 'win32' else time
        else:
            self.time_function = time_function

    def __enter__(self):
        parent = inspect.currentframe().f_back
        try:
            if parent.f_code.co_flags & inspect.CO_NEWLOCALS:
                raise RuntimeError("timers only work when invoked at the module/script level")
            self._with_start = parent.f_lasti
        finally:
            del parent
        gc_enabled = gc.isenabled()
        gc.disable()
        self._gc_enabled = gc_enabled
        self._start_time = self.time_function()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_value is None:
            duration = self.time_function() - self._start_time

            loops = self.loops or self._estimate_loop_count(duration, 1)

            parent = inspect.currentframe().f_back

            try:
                new_code = self._build_loop_code(parent.f_code, with_start=self._with_start, with_end=parent.f_lasti, loop_count=loops)

                results = []
                for r in range(self.repeat):
                    start_time = self.time_function()
                    exec(new_code, parent.f_globals, parent.f_locals)
                    duration = self.time_function() - start_time
                    if not self.loops and not results and duration < 0.2 and loops < 10**9:  # the first estimate may have been inaccurate when the duration is very small
                        # loops = self._estimate_loop_count(duration, loops)
                        while duration < 0.2 and loops < 10**9:
                            duration *= 10
                            loops *= 10
                        new_code = self._adjust_loop_count(new_code, loops)
                        start_time = self.time_function()
                        exec(new_code, parent.f_globals, parent.f_locals)
                        duration = self.time_function() - start_time
                    results.append(duration)

                execution_time = min(results)  # best time out of repeat tries
                statement_time = execution_time / loops
                statement_rate = 1 / statement_time

                normalized_time, time_unit = normalize_time(statement_time)

                if self.description is not None:
                    format_string = u"{} loops, best of {}: {:.{precision}g} {} per loop ({:.{rate_precision}f} operations/sec); {description}"
                else:
                    format_string = u"{} loops, best of {}: {:.{precision}g} {} per loop ({:.{rate_precision}f} operations/sec)"
                rate_precision = 2 if statement_rate < 10 else 1 if statement_rate < 100 else 0
                print format_string.format(loops, self.repeat, normalized_time, time_unit, statement_rate, description=self.description, precision=3, rate_precision=rate_precision)
            finally:
                del parent
                if self._gc_enabled:
                    gc.enable()
        del self._start_time, self._with_start, self._gc_enabled

    @staticmethod
    def _build_loop_code(o_code, with_start, with_end, loop_count):
        code = type(o_code)

        # With statement:
        #
        # Header:
        #
        #              0 LOAD_GLOBAL              n (context_manager)
        #              3 SETUP_WITH              xx (to zz+4)
        #              6 STORE_FAST               m (context_manager variable (with ... as foobar))
        #
        # Body:
        #              9 <code_string>
        #
        # Footer:
        #
        #           zz+0 POP_BLOCK
        #           zz+1 LOAD_CONST               p (None)
        #       >>  zz+4 WITH_CLEANUP
        #           zz+5 END_FINALLY
        #           zz+6 LOAD_CONST               p (None)
        #           zz+9 RETURN_VALUE

        code_start = with_start + 3  # move past the SETUP_WITH opcode (1 byte opcode itself + 2 bytes delta)
        # skip the next bytecode which can be one of POP_TOP, STORE_FAST, STORE_NAME, UNPACK_SEQUENCE (POP_TOP is 1 byte, the others are 3)
        if ord(o_code.co_code[code_start]) == dis.opmap['POP_TOP']:
            code_start += 1
        else:
            code_start += 3
        code_end = with_end - 4  # at the end there is a POP_BLOCK + LOAD_CONST (index) (1 + 3 = 4 bytes)

        code_bytes = o_code.co_code[code_start:code_end]
        try:
            xrange
        except NameError:
            names = o_code.co_names + ('__loop_index', 'range')
        else:
            names = o_code.co_names + ('__loop_index', 'xrange')

        code_constants = o_code.co_consts + (loop_count,)
        loops_index = len(code_constants) - 1

        # Loop header:
        #
        #              0 SETUP_LOOP              xx (to zz+4)
        #              3 LOAD_NAME                n (xrange)
        #              6 LOAD_CONST               m (1000)
        #              9 CALL_FUNCTION            1
        #             12 GET_ITER
        #       >>    13 FOR_ITER                yy (to zz+3)
        #             16 STORE_NAME               k (__loop_index)
        #
        # Code body:
        #             19 <code_string>
        #
        # Loop footer:
        #
        #           zz+0 JUMP_ABSOLUTE           13
        #       >>  zz+3 POP_BLOCK
        #       >>  zz+4 LOAD_CONST               l (None)
        #           zz+7 RETURN_VALUE
        #
        # zz = len(code_string) + 19
        # xx +  3 == zz + 4  ->  xx = len(code_string) + 19 + 4 -  3 = len(code_string) + 20
        # yy + 16 == zz + 3  ->  yy = len(code_string) + 19 + 3 - 16 = len(code_string) + 6

        loop_header = bytearray('\x78\x00\x00\x65\x00\x00\x64\x00\x00\x83\x01\x00\x44\x5d\x00\x00\x5a\x01\x00')
        loop_footer = bytearray('\x71\x0d\x00\x57\x64\x00\x00\x53')

        struct.pack_into('=H', loop_header,  1, len(code_bytes) + 20)          # SETUP_LOOP delta (xx)
        struct.pack_into('=H', loop_header,  4, len(names) - 1)                # LOAD_NAME index for range function
        struct.pack_into('=H', loop_header,  7, loops_index)                   # LOAD_CONST index for loop count
        struct.pack_into('=H', loop_header, 14, len(code_bytes) + 6)           # FOR_ITER delta (yy)
        struct.pack_into('=H', loop_header, 17, len(names) - 2)                # STORE_NAME index for __loop_index

        struct.pack_into('=H', loop_footer,  5, o_code.co_consts.index(None))  # LOAD_CONST index for None

        new_code_bytes = bytes(loop_header) + code_bytes + bytes(loop_footer)

        # adjust the line numbers table
        class WithinCodeRange(object):
            def __init__(self, size):
                self.limit = size
                self.bytes = 0

            def __call__(self, increment_pair):
                byte_increment, line_increment = increment_pair
                self.bytes += byte_increment
                return self.bytes < self.limit

        byte_increments = deque(bytearray(o_code.co_lnotab[0::2]))
        line_increments = deque(bytearray(o_code.co_lnotab[1::2]))
        byte_offset = line_offset = 0
        while byte_offset < code_start:
            byte_offset += byte_increments.popleft()
            line_offset += line_increments.popleft()
        byte_increments.appendleft(len(loop_header))
        line_increments.appendleft(1)

        line_numbers_table = bytes(bytearray(chain.from_iterable(takewhile(WithinCodeRange(len(loop_header + code_bytes)), izip(byte_increments, line_increments)))))

        return code(o_code.co_argcount, o_code.co_nlocals, o_code.co_stacksize, o_code.co_flags, new_code_bytes, code_constants, names, o_code.co_varnames,
                    o_code.co_filename, o_code.co_name, o_code.co_firstlineno + line_offset - 1, line_numbers_table, o_code.co_freevars, o_code.co_cellvars)

    @staticmethod
    def _adjust_loop_count(o_code, new_count):
        code = type(o_code)

        # this function should only be called on code generated by _build_loop_code() as it assumes that loop_count
        # is the last entry in the constants tuple (which is how _build_loop_code builds the constants tuple)
        code_constants = o_code.co_consts[:-1] + (new_count,)

        return code(o_code.co_argcount, o_code.co_nlocals, o_code.co_stacksize, o_code.co_flags, o_code.co_code, code_constants, o_code.co_names, o_code.co_varnames,
                    o_code.co_filename, o_code.co_name, o_code.co_firstlineno, o_code.co_lnotab, o_code.co_freevars, o_code.co_cellvars)

    @staticmethod
    def _estimate_loop_count(run_time, loop_count):
        individual_time = run_time / loop_count
        for i in range(0, 10):
            loops = 10**i
            if individual_time * loops >= 0.2:
                break
        else:
            loops = 10**9
        return loops

timer = Timer


class OldTimer(object):
    def __init__(self, description=None, loops=1000000, time_function=Automatic):
        if not isinstance(loops, int):
            raise TypeError("loops should be an integer number")
        if not callable(time_function):
            raise TypeError("time_function should be a callable")
        self.description = description
        self.loops = loops
        if time_function is Automatic:
            self.time_function = clock if sys.platform == 'win32' else time
        else:
            self.time_function = time_function

    def __enter__(self):
        self._start_time = self.time_function()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_value is None:
            execution_time = self.time_function() - self._start_time
            statement_time = execution_time / self.loops
            statement_rate = 1 / statement_time

            normalized_time, time_unit = normalize_time(statement_time)

            if self.description is not None:
                format_string = u"{} loops: {:.{precision}g} {} per loop ({:.{rate_precision}f} operations/sec); {description}"
            else:
                format_string = u"{} loops: {:.{precision}g} {} per loop ({:.{rate_precision}f} operations/sec)"
            rate_precision = 2 if statement_rate < 10 else 1 if statement_rate < 100 else 0
            print format_string.format(self.loops, normalized_time, time_unit, statement_rate, description=self.description, precision=3, rate_precision=rate_precision)
        del self._start_time


class TimeProbe(object):
    def __init__(self, description=None, time_function=Automatic):
        if not callable(time_function):
            raise TypeError("time_function should be a callable")
        self.description = description
        if time_function is Automatic:
            self.time_function = clock if sys.platform == 'win32' else time
        else:
            self.time_function = time_function

    def __enter__(self):
        # for some reason doing anything here (or in __init__) before we set the start time, will affect the total runtime significantly (not sure why).
        self._start_time = self.time_function()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_value is None:
            duration = self.time_function() - self._start_time

            probe = _MeasurementProbe(self.time_function)
            samples = probe.run(1000)

            measurement_overhead = samples.average_value
            if duration > measurement_overhead:
                duration -= measurement_overhead

            normalized_time, time_unit = normalize_time(duration)

            error = samples.sampling_unit / duration * 100
            if error >= 0.1:
                precision = 2 if error < 10 else 1 if error < 100 else 0
                # error_string = " (measurement error: {:.{precision}f}%)".format(error, precision=precision)
                error_string = " (uncertainty {:.{precision}f}%)".format(error, precision=precision)
            else:
                error_string = ""
            if self.description is not None:
                # format_string = u"{:.{precision}g} {}{}; {description}"
                format_string = u"{description}: {:.{precision}g} {}{}"
            else:
                format_string = u"{:.{precision}g} {}{}"
            print format_string.format(normalized_time, time_unit, error_string, description=self.description, precision=3)
        del self._start_time

time_probe = TimeProbe


@decorator
def measure_time(func):
    @preserve_signature(func)
    def func_wrapper(*args, **kw):
        with time_probe("executing {}".format(func.__name__)):
            return func(*args, **kw)
    return func_wrapper


class _MeasurementProbe(object):
    def __init__(self, time_function=Automatic):
        if not callable(time_function):
            raise TypeError("time_function should be a callable")
        if time_function is Automatic:
            self.time_function = clock if sys.platform == 'win32' else time
        else:
            self.time_function = time_function

    def __enter__(self):
        self._start_time = self.time_function()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_value is None:
            self.duration = self.time_function() - self._start_time
        del self._start_time

    def get_sample(self):
        with self:
            pass
        return self.duration

    def run(self, iterations=1000):
        gc_enabled = gc.isenabled()
        gc.disable()
        try:
            return _MeasurementSamples(self.get_sample() for _ in xrange(iterations))
        finally:
            if gc_enabled:
                gc.enable()


class _MeasurementSamples(tuple):
    def __init__(self, samples):
        super(_MeasurementSamples, self).__init__(samples)
        self.average_value = sum(self) / len(self)
        self.value_set = set(self)
        self.value_distribution = {value: self.count(value) for value in self.value_set}
        self.sampling_unit = min(x for x in self.value_set if x != 0) if self.value_set != {0} else 1  # assume the worst (1 second timer accuracy)


def normalize_time(run_time):
    normalized_time = run_time
    for time_unit in ('s', 'ms', 'us', 'ns'):
        if normalized_time >= 1:
            return normalized_time, time_unit
        normalized_time *= 1000
    else:
        return run_time * 1e9, 'ns'


