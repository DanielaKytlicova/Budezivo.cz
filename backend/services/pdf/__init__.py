"""PDF render layer — premium editorial reports.

This module deliberately replaces the rendering layer ONLY. The endpoint URL,
input payload shape, DB access, models, routes and frontend remain untouched.
"""
from .pdf_renderer import render_program_report

__all__ = ["render_program_report"]
