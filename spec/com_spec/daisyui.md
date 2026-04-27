# daisyui.md — UI Component Library Spec

> **What this file is:** Reference for DaisyUI components and Tailwind patterns used in this project. Read this when writing or modifying any UI component.
>
> **⚠️ Migration status:** DaisyUI and the Dioxus UI framework are both under evaluation. The current stack (Dioxus 0.5 + DaisyUI 5 + Tailwind CSS 4) may be replaced. Do not introduce new DaisyUI patterns without checking `spec/roadmap.md` first. Do not suggest switching the UI framework without asking.
>
> **Boundary:** Update this file if the UI library changes or if new patterns are established. Do not rewrite as part of a feature unless the feature changes the UI conventions.

---

# DaisyUI 5 Specification

## Overview

DaisyUI 5 is a CSS library for Tailwind CSS 4 that provides semantic class names for common UI components. It eliminates the need to write long utility class chains by offering pre-styled, themeable components with clean, readable markup.

**Official Website:** https://daisyui.com
**LLM-Friendly Documentation:** https://daisyui.com/llms.txt

## Installation

### Prerequisites

- Tailwind CSS 4 (required)
- Node.js and npm/yarn/pnpm

### Installation Steps

1. **Install DaisyUI via npm:**
   ```bash
   npm i -D daisyui@latest
   ```

2. **Add to your CSS file:**
   ```css
   @plugin "daisyui";
   ```

3. **For Tailwind CSS 3 compatibility,** use the traditional plugin approach in `tailwind.config.js`:
   ```javascript
   module.exports = {
     plugins: [require("daisyui")],
   }
   ```

## Core Components

DaisyUI provides 60+ pre-styled components. Below are the most commonly used components with their semantic class names.

### Buttons

```html
<!-- Basic button -->
<button class="btn">Button</button>

<!-- Button variants -->
<button class="btn btn-primary">Primary</button>
<button class="btn btn-secondary">Secondary</button>
<button class="btn btn-accent">Accent</button>
<button class="btn btn-ghost">Ghost</button>
<button class="btn btn-link">Link</button>

<!-- Button sizes -->
<button class="btn btn-xs">Tiny</button>
<button class="btn btn-sm">Small</button>
<button class="btn btn-md">Medium</button>
<button class="btn btn-lg">Large</button>

<!-- Button states -->
<button class="btn" disabled>Disabled</button>
<button class="btn btn-loading">Loading</button>

<!-- Outline buttons -->
<button class="btn btn-outline">Outline</button>
<button class="btn btn-outline btn-primary">Primary Outline</button>
```

### Cards

```html
<div class="card bg-base-100 w-96 shadow-xl">
  <figure>
    <img src="/images/photo.jpg" alt="Photo" />
  </figure>
  <div class="card-body">
    <h2 class="card-title">Card Title</h2>
    <p>Card content goes here.</p>
    <div class="card-actions justify-end">
      <button class="btn btn-primary">Buy Now</button>
    </div>
  </div>
</div>
```

### Navigation

#### Navbar
```html
<div class="navbar bg-base-100">
  <div class="flex-1">
    <a class="btn btn-ghost text-xl">daisyUI</a>
  </div>
  <div class="flex-none">
    <ul class="menu menu-horizontal px-1">
      <li><a>Item 1</a></li>
      <li><a>Item 2</a></li>
    </ul>
  </div>
</div>
```

#### Menu
```html
<ul class="menu bg-base-200 rounded-box w-56">
  <li><a>Item 1</a></li>
  <li><a>Item 2</a></li>
  <li>
    <details>
      <summary>Parent</summary>
      <ul>
        <li><a>Child 1</a></li>
        <li><a>Child 2</a></li>
      </ul>
    </details>
  </li>
</ul>
```

### Forms

#### Input Fields
```html
<input type="text" placeholder="Type here" class="input input-bordered w-full max-w-xs" />
<input type="text" placeholder="Primary" class="input input-primary input-bordered" />
<input type="text" placeholder="Error" class="input input-error input-bordered" />
<input type="text" disabled placeholder="Disabled" class="input input-bordered" />
```

#### Select
```html
<select class="select select-bordered w-full max-w-xs">
  <option disabled selected>Pick your favorite</option>
  <option>Option 1</option>
  <option>Option 2</option>
</select>
```

#### Checkbox
```html
<input type="checkbox" class="checkbox checkbox-primary" />
<input type="checkbox" class="checkbox checkbox-secondary" />
<input type="checkbox" class="checkbox checkbox-accent" />
```

#### Toggle (Switch)
```html
<input type="checkbox" class="toggle toggle-primary" />
<input type="checkbox" class="toggle toggle-secondary" />
<input type="checkbox" class="toggle toggle-accent" />
```

#### Radio
```html
<input type="radio" name="radio-1" class="radio radio-primary" />
<input type="radio" name="radio-1" class="radio radio-secondary" />
```

#### Textarea
```html
<textarea class="textarea textarea-bordered" placeholder="Bio"></textarea>
```

### Modals

```html
<!-- Open modal using label -->
<label for="my_modal_7" class="btn">Open Modal</label>
<input type="checkbox" id="my_modal_7" class="modal-toggle" />
<div class="modal" role="dialog">
  <div class="modal-box">
    <h3 class="text-lg font-bold">Hello!</h3>
    <p class="py-4">This modal works with a hidden checkbox!</p>
    <div class="modal-action">
      <label for="my_modal_7" class="btn">Close!</label>
    </div>
  </div>
</div>
```

### Alerts

```html
<div class="alert alert-info">
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
  <span>New software update available.</span>
</div>

<div class="alert alert-success">
  <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
  <span>Your purchase has been confirmed!</span>
</div>

<div class="alert alert-warning">
  <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
  <span>Warning: Invalid email address!</span>
</div>

<div class="alert alert-error">
  <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
  <span>Error! Task failed successfully.</span>
</div>
```

### Tables

```html
<div class="overflow-x-auto">
  <table class="table">
    <thead>
      <tr>
        <th>Name</th>
        <th>Job</th>
        <th>Favorite Color</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Cy Ganderton</td>
        <td>Quality Control Specialist</td>
        <td>Blue</td>
      </tr>
      <tr>
        <td>Hart Hagerty</td>
        <td>Desktop Support Technician</td>
        <td>Purple</td>
      </tr>
    </tbody>
  </table>
</div>
```

### Badges

```html
<div class="badge">Badge</div>
<div class="badge badge-primary">Primary</div>
<div class="badge badge-secondary">Secondary</div>
<div class="badge badge-accent">Accent</div>
<div class="badge badge-ghost">Ghost</div>
<div class="badge badge-outline">Outline</div>
```

### Progress Bars

```html
<progress class="progress progress-primary w-56" value="70" max="100"></progress>
<progress class="progress progress-secondary w-56" value="30" max="100"></progress>
<progress class="progress progress-accent w-56" value="50" max="100"></progress>
```

### Tooltips

```html
<div class="tooltip" data-tip="Tooltip message">
  <button class="btn">Hover me</button>
</div>

<div class="tooltip tooltip-primary" data-tip="Primary tooltip">
  <button class="btn">Hover me</button>
</div>
```

### Dropdowns

```html
<div class="dropdown">
  <div tabindex="0" role="button" class="btn m-1">Click</div>
  <ul tabindex="0" class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-52">
    <li><a>Item 1</a></li>
    <li><a>Item 2</a></li>
  </ul>
</div>
```

### Tabs

```html
<div role="tablist" class="tabs tabs-boxed">
  <a role="tab" class="tab">Tab 1</a>
  <a role="tab" class="tab tab-active">Tab 2</a>
  <a role="tab" class="tab">Tab 3</a>
</div>
```

### Toast Notifications

```html
<div class="toast toast-top toast-end">
  <div class="alert alert-info">
    <span>New message arrived.</span>
  </div>
</div>
```

## Theming System

DaisyUI supports 30+ built-in themes and custom theme creation.

### Available Themes

- `light` - Default light theme
- `dark` - Default dark theme
- `cupcake` - Light, pastel colors
- `bumblebee` - Yellow/black theme
- `emerald` - Green-based theme
- `corporate` - Professional blue theme
- `synthwave` - Neon retro theme
- `retro` - Vintage warm colors
- `cyberpunk` - Bright neon theme
- `valentine` - Pink/romantic theme
- `halloween` - Orange/black theme
- `garden` - Nature-inspired green
- `forest` - Dark green theme
- `aqua` - Cyan/blue theme
- `lofi` - Minimal grayscale
- `pastel` - Soft pastel colors
- `fantasy` - Purple/magical theme
- `wireframe` - Wireframe style
- `black` - Pure black theme
- `luxury` - Elegant dark theme
- `dracula` - Dracula dark theme
- `cmyk` - CMYK color model
- `autumn` - Fall colors
- `business` - Corporate blue
- `acid` - Acid bright colors
- `lemonade` - Lemon yellow theme
- `night` - Dark blue theme
- `coffee` - Coffee brown theme
- `winter` - Icy blue theme
- `dim` - Dimmed colors
- `nord` - Nord palette
- `sunset` - Sunset orange/pink

### Applying Themes

Apply themes globally or per-component:

```html
<!-- Global theme -->
<html data-theme="dark">

<!-- Component-level theme -->
<div class="bg-base-100" data-theme="cupcake">
  <!-- Content uses cupcake theme -->
</div>
```

### Theme Configuration

Configure themes in `tailwind.config.js`:

```javascript
module.exports = {
  // ... other config
  daisyui: {
    themes: ["light", "dark", "cupcake"], // Enable specific themes
    darkTheme: "dark", // Set default dark theme
    base: true, // Apply base styles
    styled: true, // Include component styles
    utils: true, // Include utility classes
    logs: true, // Show theme change logs
  },
}
```

### Custom Theme Creation

Create custom themes by defining color values:

```javascript
module.exports = {
  daisyui: {
    themes: [
      "light",
      "dark",
      {
        mytheme: {
          "primary": "#ff0000",
          "secondary": "#00ff00",
          "accent": "#0000ff",
          "neutral": "#333333",
          "base-100": "#ffffff",
          "info": "#0000ff",
          "success": "#00ff00",
          "warning": "#ffff00",
          "error": "#ff0000",
        },
      },
    ],
  },
}
```

## Color System

DaisyUI uses semantic color names that adapt to the current theme:

- **`primary`** - Main brand color
- **`secondary`** - Secondary brand color
- **`accent`** - Accent/highlight color
- **`neutral`** - Neutral/background color
- **`base-100`** - Base background color
- **`base-200`** - Slightly darker base
- **`base-300`** - Even darker base
- **`info`** - Informational messages
- **`success`** - Success/positive messages
- **`warning`** - Warning/caution messages
- **`error`** - Error/danger messages

### Using Colors

```html
<!-- Semantic color classes -->
<div class="bg-primary text-primary-content">Primary background</div>
<div class="bg-secondary text-secondary-content">Secondary background</div>
<div class="bg-accent text-accent-content">Accent background</div>
<div class="bg-neutral text-neutral-content">Neutral background</div>
<div class="bg-base-100">Base background</div>
```

## Best Practices

### 1. Use Semantic Classes

Prefer semantic component classes over raw Tailwind utilities:

```html
<!-- Good -->
<button class="btn btn-primary">Click Me</button>

<!-- Avoid -->
<button class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">Click Me</button>
```

### 2. Leverage Built-in Themes

Use DaisyUI's theme system instead of hardcoding colors:

```html
<!-- Good -->
<div class="bg-base-100 text-base-content">Content</div>

<!-- Avoid -->
<div class="bg-white text-gray-900">Content</div>
```

### 3. Combine with Tailwind Utilities

DaisyUI components work seamlessly with Tailwind utilities:

```html
<button class="btn btn-primary w-full max-w-xs mx-auto">Full Width Button</button>
```

### 4. Responsive Design

Use Tailwind's responsive prefixes with DaisyUI components:

```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  <div class="card bg-base-100 shadow-xl">Card 1</div>
  <div class="card bg-base-100 shadow-xl">Card 2</div>
  <div class="card bg-base-100 shadow-xl">Card 3</div>
</div>
```

### 5. Accessibility

- Use proper ARIA roles where needed
- Ensure sufficient color contrast (themes handle this automatically)
- Provide labels for form inputs
- Use semantic HTML elements

```html
<label class="label">
  <span class="label-text">Email</span>
</label>
<input type="email" class="input input-bordered" aria-label="Email address" />
```

### 6. Performance

- Only enable themes you actually use in configuration
- Consider code splitting for large applications
- Use tree-shaking compatible build tools

## Integration with Frameworks

### React/JSX

```jsx
import React from 'react';

function MyComponent() {
  return (
    <div className="card bg-base-100 shadow-xl">
      <div className="card-body">
        <h2 className="card-title">Card Title</h2>
        <p>Card content</p>
        <button className="btn btn-primary">Action</button>
      </div>
    </div>
  );
}
```

### Vue

```vue
<template>
  <div class="card bg-base-100 shadow-xl">
    <div class="card-body">
      <h2 class="card-title">Card Title</h2>
      <p>Card content</p>
      <button class="btn btn-primary">Action</button>
    </div>
  </div>
</template>
```

### Dioxus (Rust)

```rust
fn app() -> Element {
    rsx! {
        div { class: "card bg-base-100 shadow-xl",
            div { class: "card-body",
                h2 { class: "card-title", "Card Title" }
                p { "Card content" }
                button { class: "btn btn-primary", "Action" }
            }
        }
    }
}
```

## Common Patterns

### Centered Card Layout

```html
<div class="min-h-screen flex items-center justify-center bg-base-200">
  <div class="card bg-base-100 w-96 shadow-xl">
    <div class="card-body">
      <h2 class="card-title">Welcome</h2>
      <p>Content goes here</p>
    </div>
  </div>
</div>
```

### Responsive Grid

```html
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
  <!-- Cards -->
</div>
```

### Form with Validation States

```html
<div class="form-control w-full max-w-xs">
  <label class="label">
    <span class="label-text">Username</span>
  </label>
  <input type="text" placeholder="Enter username" class="input input-bordered" />
  <label class="label">
    <span class="label-text-alt text-error">Username is required</span>
  </label>
</div>
```

### Loading States

```html
<button class="btn btn-loading">Loading</button>
<span class="loading loading-spinner loading-lg"></span>
<div class="skeleton h-32 w-full"></div>
```

## Troubleshooting

### Components Not Styled

- Verify DaisyUI is properly installed: `npm list daisyui`
- Check that `@plugin "daisyui"` is in your CSS file
- Ensure Tailwind CSS 4 is being used
- Rebuild your project after configuration changes

### Theme Not Switching

- Confirm theme name is spelled correctly
- Check that theme is enabled in configuration
- Clear browser cache and rebuild

### Build Errors

- Update to latest DaisyUI version: `npm update daisyui`
- Verify Tailwind CSS version compatibility
- Check for conflicting CSS frameworks

## Resources

- **Official Documentation:** https://daisyui.com
- **LLM-Friendly Docs:** https://daisyui.com/llms.txt
- **GitHub Repository:** https://github.com/saadeghi/daisyui
- **Playground:** https://daisyui.com/playground
- **Themes Preview:** https://daisyui.com/themes

## Version Notes

This specification covers **DaisyUI 5**, which requires **Tailwind CSS 4**. For projects using Tailwind CSS 3, use DaisyUI 4.x with the traditional plugin configuration method.

Key differences in v5:
- Uses `@plugin` directive instead of JavaScript plugin registration
- Improved performance and smaller bundle size
- Enhanced theming system
- Better integration with Tailwind CSS 4 features
