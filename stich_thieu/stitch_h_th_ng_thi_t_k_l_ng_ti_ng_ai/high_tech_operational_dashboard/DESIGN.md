---
name: High-Tech Operational Dashboard
colors:
  surface: '#101416'
  surface-dim: '#101416'
  surface-bright: '#363a3c'
  surface-container-lowest: '#0b0f11'
  surface-container-low: '#181c1e'
  surface-container: '#1c2022'
  surface-container-high: '#272b2d'
  surface-container-highest: '#313538'
  on-surface: '#e0e3e5'
  on-surface-variant: '#c2c9b1'
  inverse-surface: '#e0e3e5'
  inverse-on-surface: '#2d3133'
  outline: '#8c947d'
  outline-variant: '#424937'
  surface-tint: '#9bd93c'
  primary: '#bdfd5d'
  on-primary: '#213600'
  primary-container: '#a2e043'
  on-primary-container: '#3e6100'
  inverse-primary: '#446900'
  secondary: '#c2c7cb'
  on-secondary: '#2c3134'
  secondary-container: '#42474b'
  on-secondary-container: '#b1b6b9'
  tertiary: '#ffe4dd'
  on-tertiary: '#5e1700'
  tertiary-container: '#ffbfac'
  on-tertiary-container: '#a22e00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#b6f657'
  primary-fixed-dim: '#9bd93c'
  on-primary-fixed: '#111f00'
  on-primary-fixed-variant: '#324f00'
  secondary-fixed: '#dfe3e7'
  secondary-fixed-dim: '#c2c7cb'
  on-secondary-fixed: '#171c1f'
  on-secondary-fixed-variant: '#42474b'
  tertiary-fixed: '#ffdbd0'
  tertiary-fixed-dim: '#ffb59e'
  on-tertiary-fixed: '#3a0b00'
  on-tertiary-fixed-variant: '#852400'
  background: '#101416'
  on-background: '#e0e3e5'
  surface-variant: '#313538'
typography:
  headline-xl:
    fontFamily: Be Vietnam Pro
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Be Vietnam Pro
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Be Vietnam Pro
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: JetBrains Mono
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  data-tabular:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 16px
  margin-page: 24px
---

## Brand & Style

This design system is built for mission-critical operations, focusing on high-density data visualization and rapid decision-making. The aesthetic is **Brutalist-Experimental**, characterized by sharp edges, a command-line inspired color palette, and a focus on raw functionality over decorative elements.

The target audience is operational managers and technicians who require a deep-focus environment. The UI evokes a sense of technical precision and authoritative control through its high-contrast dark mode and technical typography. Every pixel is intentional, minimizing distraction to prioritize real-time data monitoring and task execution.

## Colors

The palette is rooted in a deep charcoal foundation (`#101416`) to eliminate glare and enhance focus. The primary action color is a high-visibility **Lime Green** (`#a2e043`), used for "New" indicators, success states, and primary CTAs. 

### Usage Guidelines:
- **Backgrounds:** Use the base neutral for the main canvas. Use the secondary color for elevated surface containers like cards or sidebar panels.
- **Accents:** The tertiary orange/red is reserved strictly for alerts, overdue statuses, or critical errors.
- **Status Spectrum:** For complex data distribution (like donut charts), utilize the expanded spectrum including Teal, Purple, and Orange to differentiate categories without sacrificing the dark-tech aesthetic.
- **Contrast:** Maintain a minimum 4.5:1 contrast ratio for all functional text against surface backgrounds.

## Typography

This system employs a dual-font strategy. **Be Vietnam Pro** provides a sophisticated, readable foundation for headlines and branding, ensuring full Vietnamese diacritic support. **JetBrains Mono** is used for all body text, labels, and data points to reinforce the technical, "terminal" aesthetic.

### Data Rendering:
All numerical data must use **tabular figures** (monospaced numbers) to ensure vertical alignment in tables and dashboards, allowing users to scan values quickly for discrepancies.

### Scaling:
For mobile views, `headline-xl` scales down to 24px. Body text remains consistent at 14px-16px to maintain legibility in high-density layouts.

## Layout & Spacing

The layout utilizes a **12-column fluid grid** for the main content area, paired with a fixed 240px left-hand navigation bar. The rhythm is based on a **4px baseline grid**, promoting a dense, data-rich environment typical of operational dashboards.

### Breakpoints:
- **Desktop (1440px+):** Full side-nav visibility, multi-pane dashboard layout.
- **Tablet (768px - 1439px):** Side-nav collapses to icons; charts reflow to single column.
- **Mobile (<767px):** Single column stack; table scrolls horizontally; navigation moves to a bottom bar or hamburger menu.

Content should utilize `md` (16px) gutters to maintain separation while maximizing screen real estate.

## Elevation & Depth

In this design system, depth is communicated through **Bold Borders** and **Tonal Layering** rather than traditional shadows. This maintains the brutalist, flat aesthetic.

- **Level 0 (Background):** `#101416` - The deepest layer.
- **Level 1 (Containers/Cards):** `#1c2124` - Used for primary widgets and data tables.
- **Level 2 (Popovers/Modals):** `#252a2d` - Highest local elevation, often outlined with a 1px solid border in a slightly lighter neutral.
- **Interactions:** Hover states for table rows or buttons should use a subtle background shift (e.g., +5% lightness) or a 1px border in the primary accent color.

## Shapes

The design system adheres to a **Sharp (0px)** corner radius for all primary UI components. This reinforces the industrial, high-tech nature of the interface. 

- **Buttons & Inputs:** Hard 90-degree corners.
- **Status Tags/Chips:** Rectangular with no rounding.
- **Cards & Containers:** Sharp edges to align perfectly with the grid.

*Note: In specific data visualization contexts (e.g., donut charts), circular geometry is permitted, but the containing widgets must remain sharp.*

## Components

### Buttons
- **Primary:** Solid `#a2e043` with black text. Sharp corners.
- **Secondary:** Transparent with a 1px `#a2e043` border.
- **Ghost:** No border, JetBrains Mono text, subtle hover highlight.

### Data Tables
- **Header:** Uppercase `label-sm` typography, low-contrast background.
- **Rows:** High-density (32px-40px height). On hover, the entire row background shifts to `#252a2d`.
- **Status Indicators:** Text-based with a subtle background tint or a left-hand 2px border "accent" to denote priority.

### Input Fields
- **Style:** Underlined or fully boxed with a 1px border.
- **Focus:** Border changes to primary Lime Green with no outer glow.
- **Labels:** Always visible, using `label-sm`.

### Status Distribution (Charts)
- Use thin-stroke donut charts. Legend items must include both the color swatch, the category name, and the percentage/value in `data-tabular` font.

### Side Navigation
- High-contrast icons. Active state is indicated by a primary color vertical bar on the far left and the icon/text switching to white or lime green.