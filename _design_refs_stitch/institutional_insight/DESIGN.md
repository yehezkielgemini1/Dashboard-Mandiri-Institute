---
name: Institutional Insight
colors:
  surface: '#f8f9ff'
  surface-dim: '#ccdbf4'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e6eeff'
  surface-container-high: '#dde9ff'
  surface-container-highest: '#d5e3fd'
  on-surface: '#0d1c2f'
  on-surface-variant: '#434750'
  inverse-surface: '#233144'
  inverse-on-surface: '#ebf1ff'
  outline: '#737781'
  outline-variant: '#c3c6d1'
  surface-tint: '#335f9c'
  primary: '#002752'
  on-primary: '#ffffff'
  primary-container: '#003d79'
  on-primary-container: '#80aaec'
  inverse-primary: '#a8c8ff'
  secondary: '#00658d'
  on-secondary: '#ffffff'
  secondary-container: '#41befd'
  on-secondary-container: '#004b69'
  tertiary: '#372400'
  on-tertiary: '#ffffff'
  tertiary-container: '#523900'
  on-tertiary-container: '#dc9d00'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d5e3ff'
  primary-fixed-dim: '#a8c8ff'
  on-primary-fixed: '#001b3c'
  on-primary-fixed-variant: '#134783'
  secondary-fixed: '#c6e7ff'
  secondary-fixed-dim: '#81cfff'
  on-secondary-fixed: '#001e2d'
  on-secondary-fixed-variant: '#004c6b'
  tertiary-fixed: '#ffdea9'
  tertiary-fixed-dim: '#ffba26'
  on-tertiary-fixed: '#271900'
  on-tertiary-fixed-variant: '#5e4100'
  background: '#f8f9ff'
  on-background: '#0d1c2f'
  surface-variant: '#d5e3fd'
typography:
  display-lg:
    fontFamily: Source Serif 4
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: 0.02em
  headline-xl:
    fontFamily: Source Serif 4
    fontSize: 36px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: 0.01em
  headline-lg:
    fontFamily: Source Serif 4
    fontSize: 28px
    fontWeight: '500'
    lineHeight: '1.3'
    letterSpacing: 0.01em
  headline-lg-mobile:
    fontFamily: Source Serif 4
    fontSize: 24px
    fontWeight: '500'
    lineHeight: '1.3'
  body-md:
    fontFamily: Source Sans 3
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: 0.01em
  body-sm:
    fontFamily: Source Sans 3
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-caps:
    fontFamily: Source Sans 3
    fontSize: 12px
    fontWeight: '700'
    lineHeight: '1'
    letterSpacing: 0.08em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 8px
  container-max: 1280px
  gutter: 32px
  section-padding: 80px
  card-gap: 24px
---

## Brand & Style
This design system embodies the authority of a global management consultancy paired with the curated aesthetic of a premium editorial publication. It is designed for high-level decision-makers who value clarity, intellectual rigor, and time-efficiency. 

The visual style is **Editorial Minimalism**. It rejects the cluttered density of traditional data dashboards in favor of a "clean white canvas" approach. The interface relies on structural whitespace and sophisticated typography to create a sense of calm and focus. Key attributes include:
*   **Intellectual Authority:** Established through the use of classical serif typography and a deep navy palette.
*   **Modern Transparency:** Achieved through subtle shadow depth and ice-blue interactive accents that prevent the design from feeling antiquated.
*   **Insight-First Architecture:** Using functional highlights to guide the eye directly to the most critical data points.

## Colors
The palette is rooted in **Mandiri Navy (#003D79)**, used primarily for headers, primary navigation, and core branding elements to signal stability and institutional trust. 

*   **Primary Action:** **Ice Blue (#00A3E0)** is reserved for interactive elements like links, buttons, and active states, providing a refreshing modern contrast to the deep navy.
*   **Functional Highlight:** **Yellow (#FFB700)** is used sparingly as a "highlighter" for key insights, callouts, or critical data metrics within a sea of text.
*   **Typography & Borders:** Text is rendered in high-contrast **Slate (#334155)** to ensure readability without the harshness of pure black. Borders use a muted Slate tint to define sections without creating "boxes."

## Typography
The typographic system creates an editorial hierarchy. **Source Serif 4** is the voice of the publication, used for all headlines and featured pull-quotes. It features generous tracking (letter spacing) and wide line heights to evoke a premium, printed-page feel.

**Source Sans 3** serves as the functional workhorse for body copy, data tables, and interface labels. Its neutral, clean forms ensure that complex research remains legible across all device sizes. 

Vertical rhythm is strictly maintained with a 1.6x line-height for body text to promote long-form reading comfort.

## Layout & Spacing
This design system utilizes a **Fixed Grid** layout for desktop (12 columns) to mimic the structured columns of a magazine. 

*   **Generous Margins:** Desktop views feature a minimum of 80px of horizontal padding to keep content centered and prestigious. 
*   **Whitespace as Divider:** Instead of heavy horizontal rules, use 80px–120px of vertical whitespace to separate major content sections.
*   **Reflow:** On mobile, the grid collapses to 4 columns with 16px gutters, while maintaining the "canvas" feel by removing background containers and allowing imagery to bleed to the edges.

## Elevation & Depth
Depth is communicated through **Subtle Shadow Depth** rather than stark layering. 
*   **Cards and Features:** Use a soft, wide-dispersion shadow (Y: 4px, Blur: 20px, Opacity: 4% Slate) to lift elements off the white canvas. 
*   **Borders:** Use 1px Slate borders (#E2E8F0) exclusively for separating navigation or distinct data sets within a page.
*   **Avoidance:** Do not use heavy inner shadows, bevels, or dark container backgrounds. The goal is to make components feel like they are resting lightly on a high-quality paper surface.

## Shapes
The shape language is **Soft (Level 1)**. While the overall aesthetic is sharp and professional, a minimal 4px (0.25rem) corner radius on buttons, images, and input fields prevents the design from feeling aggressive or "cold." This subtle rounding adds a touch of modern approachability while maintaining the structural integrity of the magazine-style layout.

## Components
*   **Magazine Cards:** These are the primary vessel for content. They must feature high-resolution imagery, a small uppercase category label in Mandiri Navy, a Source Serif 4 headline, and no visible outer border—only whitespace and the subtle shadow defined in Elevation.
*   **Buttons:** Primary buttons use a solid Ice Blue fill with white text. Secondary buttons use a Slate border and Navy text. All buttons use the "Soft" 4px radius.
*   **Insights Highlight:** A specific component for "Key Takeaways" utilizing a left-aligned 4px vertical bar in Yellow (#FFB700) and a light cream background tint to draw immediate attention.
*   **Interactive Lists:** Research indices and bibliographies should use minimal slate dividers and Ice Blue hover states for links.
*   **Category Labels:** Small, bold, all-caps sans-serif text with 0.08em tracking, used above headlines to categorize research topics (e.g., SUSTAINABILITY, MACROECONOMICS).