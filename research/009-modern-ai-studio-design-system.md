# Deep Research 009: World-Class AI Engineering Studio Design System & Craftsmanship

**Author**: `FE-01` (Lead Frontend Architect) & `ARC-01` (Lead AI Architect)  
**Date**: 2026-08-19  
**Status**: APPROVED

---

## 1. Executive Summary & Design Philosophy

Industrial engineering software historically suffers from clumsy, generic, and outdated UI patterns. Modern AI workstations (Linear, Cursor, Raycast, Vercel AI SDK, Perplexity Pro) prove that complex technical systems must be **ergonomic, visually restrained, high-contrast, and deeply responsive**.

This research establishes the **Selnikel AI Obsidian Design System**, defining exact tokens, surfaces, micro-interactions, and workspace layouts to transform Selnikel AI into a world-class AI engineering workstation.

---

## 2. Design System Tokens & Surface Ladder

### Surface Hierarchy
| Level | Token Name | Color / Style | Purpose |
| :--- | :--- | :--- | :--- |
| **0** | `canvas` | `#08090d` + ambient radial mesh | Viewport base background |
| **1** | `surface-panel` | `#0e111a` (80% opacity) + `backdrop-blur-xl` + `border-white/[0.08]` | Sidebars, main workspace cards, modal shells |
| **2** | `surface-elevated`| `#131722` (90% opacity) + `border-white/[0.08]` | Chat messages, input bars, code blocks |
| **3** | `surface-interactive`| `#181d2c` + hover `border-blue-500/40` | Clickable pills, prompt suggestion cards, buttons |

### Color Accents & Semantic Semiotics
- **Primary Accent**: Electric Cobalt (`#2563eb` to `#3b82f6`) with Cyan luminescence (`#06b6d4`).
- **Grounded Verification**: Neon Emerald (`#10b981` / `rgba(16, 185, 129, 0.15)`).
- **Engineering Calculations**: Amber/Orange (`#f59e0b` / `rgba(245, 158, 11, 0.15)`).
- **Hairline Borders**: `rgba(255, 255, 255, 0.07)` to `rgba(255, 255, 255, 0.12)`.

---

## 3. Component Architecture & Micro-Interactions

1. **Spotlight Suggestion Cards**: Mouse-tracking subtle glowing borders for prompt presets.
2. **Glassmorphic Floating Command Bar**: Sticky bottom prompt input with scope selector, active model indicator, and keyboard shortcuts (`Enter` to send, `Shift+Enter` for new line).
3. **ReAct Thought Accordion**: Animated step progression timeline with status dots, JSON arguments inspector, and observation badges.
4. **Preserved Markdown Tables**: Styled GFM tables with striped dark rows, monospace numbers, and horizontal scrollbars.
5. **Interactive Citation Chips**: Clickable citation tags with slide-over source preview auditor.
