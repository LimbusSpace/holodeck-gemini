# GLB Import Script for Holodeck
# Generated automatically

import bpy
import os
from pathlib import Path

def clear_scene():
    """Clear existing scene objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def setup_scene():
    """Setup scene configuration."""
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1.0

def import_glb_asset(glb_path, object_name=None):
    """Import a GLB asset into the scene."""
    if not os.path.exists(glb_path):
        print(f'ERROR: GLB file not found: {glb_path}')
        return None
    
    try:
        # Store previous selection
        prev_selected = set(bpy.context.selected_objects)
        
        # Import GLB using Blender's GLTF importer
        bpy.ops.import_scene.gltf(filepath=glb_path)
        
        # Get newly imported objects
        new_objects = [obj for obj in bpy.context.selected_objects if obj not in prev_selected]
        
        if new_objects:
            root_object = new_objects[0]
            if object_name:
                root_object.name = object_name
            print(f'SUCCESS: Imported {len(new_objects)} objects from {os.path.basename(glb_path)}')
            return root_object
        else:
            print(f'WARNING: No objects imported from {glb_path}')
            return None
            
    except Exception as e:
        print(f'ERROR: Failed to import {glb_path}: {e}')
        return None

def main():
    print('=== Holodeck GLB Import Started ===')
    
    # Setup scene
    clear_scene()
    setup_scene()
    
    imported_objects = []
    
    # Import obj_001.glb
    glb_path = r'workspace/sessions/2026-01-24T18-59-51Z_6c955af2/assets/obj_001.glb'
    imported_obj = import_glb_asset(glb_path, 'furniture_1')
    if imported_obj:
        imported_objects.append(imported_obj)
        # Position first object at origin
        imported_obj.location = (0, 0, 0)
    
    # Import obj_001_0af12213.glb
    glb_path = r'workspace/sessions/2026-01-24T18-59-51Z_6c955af2/assets/obj_001_0af12213.glb'
    imported_obj = import_glb_asset(glb_path, 'furniture_2')
    if imported_obj:
        imported_objects.append(imported_obj)
        # Position subsequent objects with offset
        imported_obj.location = (2.0, 0, 0)

    # Final report
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    print(f'=== Import Completed ===')
    print(f'Total mesh objects in scene: {len(mesh_objects)}')
    print(f'Successfully imported: {len(imported_objects)} assets')
    
    # Save scene
    blend_path = 'imported_glb_scene.blend'
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f'Scene saved to: {blend_path}')

if __name__ == '__main__':
    main()