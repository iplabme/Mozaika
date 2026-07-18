# Accessibility and inclusive design

## Semantic structure

```html
<html lang="en">
<main aria-label="Presentation">
  <section class="slide" id="slide-1" aria-labelledby="slide-1-title">
    <h1 id="slide-1-title">...</h1>
  </section>
</main>
```

Every slide needs a unique ID and clear heading. DOM order should match reading order.

## Keyboard

Support:

- Right/Down/PageDown/Space → next
- Left/Up/PageUp → previous
- Home → first
- End → last
- visible focus for interactive controls

Do not trap focus or require hover.

## Reduced motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
    scroll-behavior: auto !important;
  }
}
```

Avoid flashing and continuous animation behind text. Essential information must not exist only in an animation state.

## Images

- meaningful images need useful `alt`;
- decorative images use `alt=""`;
- complex charts need a visible takeaway and longer description in notes/adjacent text;
- screenshot alt text names the important state, not merely “screenshot”.

## Color and contrast

- keep strong foreground/background contrast;
- do not encode state only with red/green;
- pair color with labels, shapes, patterns, or direct annotations;
- test washed-out projector conditions.

## Text

- avoid long all-caps;
- avoid justified paragraphs;
- use adequate line height;
- do not hide essential meaning in tiny footnotes;
- expand unfamiliar abbreviations.

## Controls and links

- link text describes destination;
- controls have accessible names;
- touch targets are large;
- focus is visible;
- critical live demos have a static fallback.

## Test

- navigate without a mouse;
- enable reduced motion;
- zoom to 200%;
- inspect portrait and landscape phone sizes;
- test offline when required;
- inspect heading order and browser accessibility tree when available.
