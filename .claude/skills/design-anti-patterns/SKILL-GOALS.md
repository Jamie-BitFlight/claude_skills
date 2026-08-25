The purpose and explicit goals of the skill design-anti-patterns:

1. Recognize and avoid the generic "AI-generated UI" aesthetic (soft gradients, glassmorphism, oversized rounded corners, hero sections in dashboards, decorative copy, KPI-grid defaults) before writing any frontend code.
2. Apply a pre-flight self-check that lists default styling decisions and cross-references them against banned patterns before code generation, rather than catching them after the fact.
3. Default to concrete, bounded "normal" component standards (border radius, spacing scale, shadow depth, transition timing, container widths) modeled on Linear/Raycast/Stripe/GitHub, producing functional, honest interfaces instead of decorative ones.
4. Select color palettes correctly: prefer the project's existing palette, fall back to a randomized pick from a predefined dark/light palette set, and never invent arbitrary color combinations.
