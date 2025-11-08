# Fence Generator

![fence-thumb](https://github.com/user-attachments/assets/490531ac-be3f-4161-9837-161426268c8a)

**Author:** The French Monkey (TFMSTYLE)  
**Version:** 1.0.0  

---

## Overview

The Fence Generator creates parametric fences of various materials — **metal**, **wood**, and **stone** — using procedural mesh construction.  
It supports posts, rails, pickets, gates, and corners, providing full control over geometric proportions, style, and composition.  
Ideal for architectural modeling, environment design, or asset creation workflows where flexibility and speed are essential.

---

## Parameters

### Live Update
When enabled, the fence updates automatically whenever parameters are modified.  
This provides instant visual feedback but may reduce performance on complex setups.

---

### Fence Type
Defines the structural style and material of the fence.
- **Metal:** Tubular posts and rails with optional hollow profiles.
- **Wood:** Rectangular beams with customizable pickets and rails.
- **Stone:** Solid panels or brick-style walls.

---

### Total Length
Specifies the total horizontal span of the generated fence.

---

### Height
Controls the vertical height of the fence structure.

---

### Section Length
Determines the length of each fence segment between posts.  
The total length is divided into evenly spaced sections.

---

## Metal Parameters

### Post Radius
Radius of the cylindrical metal posts.

---

### Number of Rails
Sets how many horizontal rails are placed between posts.

---

### Rail Radius
Controls the radius (thickness) of the metal rails.

---

### Rail Type
Specifies the cross-section shape of the rails.
- **Round:** Cylindrical metal rods.
- **Square:** Box-like rails.
- **Flat:** Flat bar sections.

---

### Hollow Metal
If enabled, converts posts and rails into hollow tubes.

---

### Wall Thickness
Defines the thickness of the tube walls when Hollow Metal is enabled.

---

### Picket Profile
Sets the design of the vertical pickets.
- **Round:** Cylindrical rods.
- **Square:** Box-section pickets.
- **Spear:** Decorative spear-tipped pickets.

---

## Wood Parameters

### Post Width
Width of the square wooden posts.

---

### Rail Height
Vertical dimension of the wooden rails.

---

### Rail Thickness
Depth of the wooden rails.

---

### Rail Profile
Defines the wooden rail shape.
- **Rectangular:** Flat boards or beams.
- **Rounded:** Cylindrical rods.

---

### Picket Style
Sets the top design of wooden pickets.
- **Flat Top:** Straight rectangular finish.
- **Pyramid Top:** Sloped top design.
- **Rounded Top:** Smooth rounded finish.

---

## Stone Parameters

### Post Depth
Depth of the stone post blocks.

---

### Stone Panel Thickness
Thickness of the main stone or brick wall sections.

---

### Stone Pattern
Defines the appearance of stone wall panels.
- **Solid:** Continuous solid stone wall.
- **Bricks:** Alternating brick pattern.

---

## Picket Parameters

### Use Vertical Pickets
Enables the generation of vertical pickets between rails.

---

### Pickets (max)
Defines the maximum number of vertical pickets per section.

---

### Picket Width
Controls the width or diameter of each picket.

---

### Picket Gap
Specifies the spacing between adjacent pickets.

---

## Gate Parameters

### Add Gate
Adds a gate to one of the fence sections.

---

### Gate Width
Specifies the width of the gate opening.

---

### Gate Frame Thickness
Thickness of the frame beams surrounding the gate.

---

### Gate Infill Pickets
Determines whether the gate includes vertical pickets.

---

### Gate Span Index
Defines which section is replaced by the gate (0 = first section).

---

### Gate Type
Selects the gate configuration.
- **Single:** One swinging panel.
- **Double:** Two panels opening from the center.

---

### Gate Opening
Controls the rotation angle of the gate doors to simulate open or closed states.

---

## Corner Parameters

### Add Corner
Adds a corner turn at the end of the fence, forming an angled extension.

---

### Corner Angle
Specifies the rotation angle of the corner section in degrees.

---

## Operators

### Generate Fence
Creates or updates the fence mesh using the defined parameters.  
If a generated fence object is already selected, it will be replaced with the updated geometry.

---

### Delete Fence
Removes the selected fence object and all its associated geometry.

---

### Reset Settings
Restores all generator parameters to their default values.  
The Live Update toggle state is preserved.

---

## Usage Notes

- Choose the **Fence Type** first to define the overall construction style.
- Adjust **Section Length** and **Height** to control proportions.
- Enable **Use Vertical Pickets** for ornamental fencing.
- Use **Hollow Metal** with small **Wall Thickness** for lightweight tubular structures.
- Combine **Gate** and **Corner** options for full enclosure designs.
- Enable **Live Update** during setup and disable it for large scenes to improve performance.
- Generated geometry is fully editable and compatible with modifiers, materials, and custom UV mapping.
