You write ONE 3D scene of an animated lesson as an ES module for three.js r186, driven by the lesson kit.
The narration and the subtitles already exist; your scene shows what each sentence describes, in sync.

## Contract (the scene is rejected otherwise)
```js
export default function build(kit) {
  const { THREE, scene, camera, beats, palette, progress, ease, lerp, label, fade, random } = kit;
  // create every object ONCE here and add it to `scene`
  return {
    update(t) {
      // t = seconds since the scene started. Set positions, rotations, scales, opacity and the camera
      // from t ONLY (a pure function of t: no accumulation, no counters, no state between calls).
    },
  };
}
```
- No `import` (THREE comes from the kit), no network, no DOM, no `window`/`document`, no timers, no `Date`,
  no `Math.random` (use `const rnd = random(7)` once in build), no textures or models from files.
- Sentence i lasts from `beats[i].start` to `beats[i].end` (seconds). `progress(t, i)` goes 0 → 1 during the
  first 60% of sentence i (`progress(t, i, 0.9)` for slower), stays 0 before and 1 after. Use `ease(x)` for
  smooth motion. Animate in sentence i exactly what sentence i says (its `visual`).
- Objects that belong to a later sentence stay hidden until then: `fade(obj, ease(progress(t, i)))` (fade sets
  `visible` and the opacity of every material).

## Look
- Schematic, clean, not photoreal: simple geometry (Box, Sphere, Cylinder, Torus, Capsule, Cone, Plane, Tube,
  InstancedMesh for many small parts), `MeshStandardMaterial({ color: palette.blue, roughness: 0.5 })`,
  transparent materials for beams, volumes and fields. Lights already exist (hemisphere + sun).
- Palette: palette.text, muted, blue, orange, green, purple, red, yellow, gray, teal, skin, bone, organ. One color
  per concept, kept across the scene.
- Scale: keep the main objects within about 8 units around the origin.

## Camera and labels (checked at the end of every sentence; a violation fails the render)
- The camera starts at (0, 3, 12) looking at (0, 0, 0). Move it smoothly with lerp/ease inside update(t) and
  always call `camera.lookAt(...)` after moving it. Keep every object the sentence talks about in view.
- `label(text, { height: 0.42, color })` → a Sprite that always faces the camera (short terms, at most 3 words).
  Place it beside its object, offset so labels never cover each other. Every visible label must stay inside the
  screen and above the bottom 17% (the subtitle band) for the camera position of that moment. Hide labels you
  no longer need with `fade(sprite, 0)`. At most 4 labels visible at once.

## Spatial clarity
- Show structure and motion that 2D cannot: rotation around an axis, depth, slices through a volume, a beam
  crossing a body, parts that separate and come back.
- Cross-sections and slices: thin `BoxGeometry` planes or clipping by scale; volumes of voxels with
  `InstancedMesh` (set each instance matrix once in build, animate the whole mesh in update).

Keep the module compact: about 120–220 lines, short helper functions, no long comments, no generic
utility libraries.

Answer only with JSON: {"code": "<the complete JavaScript module>"}.
