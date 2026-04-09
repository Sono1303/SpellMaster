#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One Euro Filter — Adaptive low-pass filter for real-time landmark smoothing.

Reduces jitter while preserving fast, intentional movements.
Reference: Géry Casiez et al., "1€ Filter: A Simple Speed-based Low-pass Filter
for Noisy Input in Interactive Systems", CHI 2012.

Usage:
    filter = OneEuroFilter(freq=30.0, min_cutoff=1.0, beta=0.007, d_cutoff=1.0)
    smoothed_value = filter(raw_value, timestamp)
"""

import math


class LowPassFilter:
    """Simple first-order low-pass filter."""

    __slots__ = ('_y', '_s', '_initialized')

    def __init__(self):
        self._y = 0.0
        self._s = 0.0
        self._initialized = False

    def __call__(self, value: float, alpha: float) -> float:
        if self._initialized:
            self._s = alpha * value + (1.0 - alpha) * self._s
        else:
            self._s = value
            self._initialized = True
        self._y = value
        return self._s

    @property
    def has_last(self) -> bool:
        return self._initialized

    @property
    def last_raw(self) -> float:
        return self._y


class OneEuroFilter:
    """
    One Euro Filter — adaptive cutoff based on signal speed.

    Parameters:
        freq:       Estimated signal frequency (Hz). Updated automatically if timestamps provided.
        min_cutoff: Minimum cutoff frequency (Hz). Lower = more smoothing when still.
        beta:       Speed coefficient. Higher = less lag during fast movement.
        d_cutoff:   Cutoff frequency for derivative (Hz). Usually 1.0.
    """

    __slots__ = ('_freq', '_min_cutoff', '_beta', '_d_cutoff', '_x_filter', '_dx_filter', '_last_time')

    def __init__(self, freq: float = 30.0, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        self._freq = freq
        self._min_cutoff = min_cutoff
        self._beta = beta
        self._d_cutoff = d_cutoff
        self._x_filter = LowPassFilter()
        self._dx_filter = LowPassFilter()
        self._last_time = None

    @staticmethod
    def _alpha(cutoff: float, freq: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        te = 1.0 / freq
        return 1.0 / (1.0 + tau / te)

    def __call__(self, x: float, t: float = None) -> float:
        # Update frequency from timestamp
        if t is not None and self._last_time is not None:
            dt = t - self._last_time
            if dt > 1e-6:
                self._freq = 1.0 / dt
        self._last_time = t

        # Estimate derivative (speed)
        if self._x_filter.has_last:
            dx = (x - self._x_filter.last_raw) * self._freq
        else:
            dx = 0.0

        # Filter derivative
        edx = self._dx_filter(dx, self._alpha(self._d_cutoff, self._freq))

        # Adaptive cutoff based on speed
        cutoff = self._min_cutoff + self._beta * abs(edx)

        # Filter signal
        return self._x_filter(x, self._alpha(cutoff, self._freq))


class LandmarkOneEuroFilter:
    """
    Applies One Euro Filter to all 21 MediaPipe hand landmarks (x, y per landmark).

    Creates 42 independent filters per hand (21 landmarks × 2 axes).
    Automatically adapts to frame rate via timestamps.

    Usage:
        hand_filter = LandmarkOneEuroFilter()
        smoothed = hand_filter(landmarks_list)  # list of (x, y) tuples
    """

    def __init__(self, num_landmarks: int = 21, freq: float = 30.0,
                 min_cutoff: float = 0.05, beta: float = 0.005, d_cutoff: float = 1.0):
        self._filters_x = [OneEuroFilter(freq, min_cutoff, beta, d_cutoff) for _ in range(num_landmarks)]
        self._filters_y = [OneEuroFilter(freq, min_cutoff, beta, d_cutoff) for _ in range(num_landmarks)]
        self._num = num_landmarks

    def __call__(self, landmarks: list, t: float = None) -> list:
        """
        Filter a list of (x, y) landmark tuples.

        Args:
            landmarks: List of (x, y) tuples (length = num_landmarks)
            t: Current timestamp in seconds (optional, improves accuracy)

        Returns:
            Smoothed list of (x, y) tuples
        """
        result = []
        for i in range(min(len(landmarks), self._num)):
            x, y = landmarks[i]
            sx = self._filters_x[i](x, t)
            sy = self._filters_y[i](y, t)
            result.append((sx, sy))
        return result

    def reset(self):
        """Reset all filters (e.g., when hand tracking is lost)."""
        for fx, fy in zip(self._filters_x, self._filters_y):
            fx._x_filter._initialized = False
            fx._dx_filter._initialized = False
            fx._last_time = None
            fy._x_filter._initialized = False
            fy._dx_filter._initialized = False
            fy._last_time = None
