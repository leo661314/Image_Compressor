# Image_Compressor

A Python CLI tool that compresses images to a **target maximum file size (KB)** while maintaining the **best possible visual quality** within defined constraints.

This repository is intentionally designed for two audiences:
1) **Users** who want a simple tool to shrink images to a given size.
2) **Interview/engineering reviewers** who want to see clear **top-down design**, **trade-off reasoning**, and an **algorithmic approach (binary search)** to a real-world “black-box” problem.

---

## Table of Contents

- [What This Tool Does](#what-this-tool-does)
- [Supported Formats](#supported-formats)
- [Installation](#installation)
- [Usage](#usage)
  - [Common Examples](#common-examples)
  - [CLI Arguments](#cli-arguments)
- [Behavior and Guarantees](#behavior-and-guarantees)
  - [Lossy Outputs (JPG/WebP)](#lossy-outputs-jpgwebp)
  - [PNG Output Policy](#png-output-policy)
  - [Transparency (Alpha) Handling](#transparency-alpha-handling)
- [Engineering Notes (Design and Thinking)](#engineering-notes-design-and-thinking)
  - [Top-Down Main Flow](#top-down-main-flow)
  - [Why Dispatch by Output Format](#why-dispatch-by-output-format)
  - [Black-Box Nature of “Target Size”](#black-box-nature-of-target-size)
  - [Algorithm: Highest Feasible Quality via Binary Search](#algorithm-highest-feasible-quality-via-binary-search)
  - [Static Bounds + Dynamic Probe](#static-bounds--dynamic-probe)
  - [Pseudocode](#pseudocode)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [License](#license)

---

## What This Tool Does

Given:
- an **input image** (e.g., JPG/PNG), and
- a **target maximum file size** (e.g., 300KB), and
- an **output format** (e.g., WebP/JPG/PNG)

the tool produces an output image that:
- attempts to be **≤ target_kb**, and
- for JPG/WebP chooses the **highest feasible quality** that satisfies the size constraint, and
- writes results to an output directory to avoid overwriting the original.

---

## Supported Formats

### Input
- JPG / JPEG
- PNG

### Output
- JPG
- WebP
- PNG

> Note: Output format determines compression strategy. JPG/WebP support a `quality` knob suitable for binary search; PNG typically does not.

---

## Installation

### Requirements
- Python 3.10+ recommended

### Install dependencies
```bash
pip install pillow
