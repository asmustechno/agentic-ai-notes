# 🎨 Diagram style guide

Hand-made SVG diagrams live in this folder. Use them only for overview graphics that Mermaid cannot draw well, such as the agent anatomy, the memory hierarchy or the autonomy spectrum. For flows, sequences and state machines, use Mermaid directly in the page.

## File naming

`NN-topic-name.svg`, where `NN` is the chapter number. Keep the editable source next to it with the same name: `NN-topic-name.excalidraw`.

Example: `01-anatomy-of-an-agent.svg` and `01-anatomy-of-an-agent.excalidraw`.

## Palette

Six colours, used with the same meaning everywhere:

| Role | Fill | Stroke / text | Use for |
| --- | --- | --- | --- |
| Model | `#E0E7FF` | `#3730A3` | The LLM, reasoning, "think" steps |
| Tools | `#CCFBF1` | `#115E59` | Tools, actions, external systems |
| Memory & data | `#FEF3C7` | `#92400E` | Memory, documents, vector stores |
| User & human | `#FCE7F3` | `#9D174D` | Users, human approval |
| Risk & errors | `#FEE2E2` | `#991B1B` | Failures, attacks, guardrails |
| Neutral | `#F1F5F9` | `#334155` | Containers, labels, everything else |

## Shapes and text

- **Background:** every SVG has a full-size rounded rectangle with fill `#FFFFFF` behind the content. This keeps it readable in GitHub dark mode, where a transparent background would put dark text on a dark page.
- **Boxes:** rounded corners (`rx="10"`), 2 px stroke.
- **Arrows:** 2 px, stroke `#334155`, with a label on every arrow that carries meaning ("calls", "returns", "stores").
- **Font:** `font-family="Inter, 'Segoe UI', Helvetica, Arial, sans-serif"`. Titles 20 px bold, labels 14 px. No text smaller than 12 px.
- **Size:** design at 960 px wide or less; set `viewBox` so it scales.

## Accessibility

- Include `<title>` and `<desc>` elements inside every SVG.
- Embed with alt text, and put an italic caption under it:

```markdown
![The five parts of an agent: model, instructions, tools, memory and loop](../../assets/diagrams/01-anatomy-of-an-agent.svg)

*The loop is what turns a model into an agent: it keeps calling the model until the goal is met.*
```

## Rights

Only original diagrams. Never trace, copy or hot-link images from papers, blogs or vendor docs. If you are inspired by a published figure, draw your own version and cite the source in the page's Further reading.
