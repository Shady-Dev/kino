# Where a menu button's menu opens

What was read before moving the sheet's ticket menu under its dots button on 2026-11-01. The
decision is in [docs/archive/2026-09-app.md](../archive/2026-09-app.md), "The ticket menu
opens under its dots".

## Findings

- **WAI-ARIA APG, Menu Button pattern**, read 2026-11-01
  (https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/). Enter and Space on the button
  open the menu and focus its first item. Down Arrow and Up Arrow on the button are
  optional. The page says nothing about where the menu is drawn relative to the button.
- **WAI-ARIA APG, Menu and Menubar pattern**, read 2026-11-01
  (https://www.w3.org/WAI/ARIA/apg/patterns/menubar/). Escape closes the menu and returns
  focus to the element that opened it. Down and Up Arrow move between items, and wrapping
  is optional. Tab leaves the menu and closes it.
- **Floating UI, computePosition**, read 2026-11-01
  (https://floating-ui.com/docs/computePosition). A placement is a side and an optional
  alignment. `bottom-end` puts the floating element below its reference, aligned to the
  reference's end side. The default is `bottom`. `flip` switches to the opposite side
  when the element would overflow its clipping container, and `shift` moves it along the
  side to keep it in view.
- **Floating UI, detectOverflow**, read 2026-11-01
  (https://floating-ui.com/docs/detectOverflow). The boundary defaults to the clipping
  ancestors and the root boundary to the viewport. `padding` adds space inside the
  boundary that counts as overflow.

## Inferences

- The reference element is the button, which is what a pointer clicked. The menu's
  previous anchor was the ticket's left edge, which sits up to the ticket's width away from it.
- The sheet body scrolls (`overflow-y:auto`), which makes it clip sideways too. It is the
  clipping ancestor Floating UI would measure against, and a desktop sheet's body edge is
  inside the viewport.

## Implementation status

Built as `menuPlace()` in `index.html`: `bottom-end` with a 4 px offset, a flip when the
visible body has less room below than the menu needs and more above, and a shift that keeps
16 px inside the body's visible rect. The keyboard handling was already the APG's and is
unchanged. Nothing further is open.
