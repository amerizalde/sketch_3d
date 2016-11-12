import bpy

from bpy.types import Operator, Panel

bl_info = {
         "name" : "Sketch 3D",
         "author" : "Andrew Merizalde <andrewmerizalde@hotmail.com>",
         "version" : (1, 0, 0),
         "blender" : (2, 7, 8),
         "location" : "View 3D > Object Mode > Tool Properties > Sketch3D",
         "description" :
             "Jump straight into a 3D sketch workflow.",
         "warning" : "",
         "wiki_url" : "https://github.com/amerizalde/sketch_3d",
         "tracker_url" : "",
         "category" : "Paint"}


def lock_toggle(context):
    if context.region_data.lock_rotation:
        context.region_data.lock_rotation = False
    else:
        context.region_data.lock_rotation = True

def setup_grease_pencil_for_sketching(context):
    context.scene.tool_settings.grease_pencil_source = 'OBJECT'
    context.scene.tool_settings.gpencil_stroke_placement_view3d = 'CURSOR'
    context.space_data.lock_cursor = True
    context.space_data.show_manipulator = False

def grease_to_curve(context):
    old_object = context.active_object
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='GPENCIL_EDIT')

    bpy.ops.gpencil.convert(type='PATH', use_timing_data=True)
    bpy.ops.gpencil.layer_remove()
    context.scene.objects.active = context.selected_objects[0]
    
    # beautify the curve
    data = context.object.data
    data.fill_mode = 'FULL'
    data.extrude = 0.833333
    data.bevel_depth = 0.833333
    data.bevel_resolution = 1
    data.resolution_u = 6
    data.splines[0].order_u = 6
    data.splines[0].use_smooth = True

    bpy.ops.object.select_pattern(pattern="GP_Layer*", extend=False)
    bpy.ops.object.join()

    context.scene.objects.active = old_object
    bpy.ops.object.mode_set(mode='EDIT')

def curve_to_mesh(context):
    old_object = context.active_object
    print(old_object.name)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.object.select_pattern(pattern="GP_Layer*", extend=False)
    context.scene.objects.active = context.selected_objects[0]
    bpy.ops.object.convert(target='MESH')

    context.object.name = "SketchMesh"

    context.scene.objects.active = old_object
    bpy.ops.object.mode_set(mode='EDIT')

class ViewLocker(Operator):

    bl_idname = "alm.view_locker"
    bl_label = "Sketch View Locker"

    def execute(self, context):
        lock_toggle(context)
        return {'FINISHED'}

class SketchOperator(Operator):

    bl_idname = "alm.grease_sketch"
    bl_label = "Create a new sketch object/ continue sketching"

    def execute(self, context):

        if "sketch_object" not in [o.name for o in bpy.data.objects.values()]:
            if context.object:
                bpy.ops.object.mode_set(mode = 'OBJECT')

            bpy.ops.mesh.primitive_vert_add()
            context.object.name = "sketch_object"        
            bpy.ops.object.mode_set(mode = 'EDIT')

            # if there is no material, add one.
            if not isinstance(context.active_object.active_material, bpy.types.Material):
                mat_name = "SketchMat"
                mat = bpy.data.materials.new(mat_name)
                mat.use_nodes = True
                
                context.active_object.data.materials.append(mat)

                # clear all nodes to start clean
                nodes = mat.node_tree.nodes
                for node in nodes:
                    nodes.remove(node)

                # create emission node
                node_emission = nodes.new(type='ShaderNodeEmission')
                node_emission.inputs[0].default_value = (1,1,1,1)
                node_emission.inputs[1].default_value = 1.0
                node_emission.location = 0,0

                # create output node
                node_output = nodes.new(type='ShaderNodeOutputMaterial')   
                node_output.location = 400,0
                
                # link nodes
                links = mat.node_tree.links
                link = links.new(node_emission.outputs[0], node_output.inputs[0])
                            
                context.active_object.active_material = mat
            
            setup_grease_pencil_for_sketching(context)
        else:
            context.scene.objects.active = bpy.data.objects["sketch_object"]
            bpy.ops.object.mode_set(mode='EDIT')

        self.report({"INFO"}, "Sketch Mode.")
        return {'FINISHED'}

class CurveOperator(Operator):

    bl_idname = "alm.grease_to_curve"
    bl_label = "Create a curve from gpencil stroke(s)"

    @classmethod
    def poll(cls, context):

        if context.scene.grease_pencil != None:
            if context.scene.grease_pencil.layers != None:
                return context.scene.grease_pencil.layers.active_index != -1

        if context.active_object != None:
            if context.active_object.grease_pencil != None:
                if context.active_object.grease_pencil.layers != None:
                    return context.active_object.grease_pencil.layers.active_index != -1
        return False
    
    def execute(self, context):
        grease_to_curve(context)
        return {'FINISHED'}

class MeshOperator(Operator):

    bl_idname = "alm.curve_to_mesh"
    bl_label = "Create a mesh from curves"
    
    @classmethod
    def poll(cls, context):
        return 'GP_Layer' in [o.name for o in context.selectable_objects]
    
    def execute(self, context):
        curve_to_mesh(context)
        return {'FINISHED'}


class AddonPanel(Panel):
    bl_label = "Sketch 3D"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = "Tools"

    def draw(self, context):
        layout = self.layout

        if context.object:
            obj = context.object
            row = layout.row()
            row.label(text="Active object is: " + obj.name)
            row = layout.row()
            row.prop(obj, "name")

        row = layout.row()
        row.operator("alm.grease_sketch", text='Sketch Mode')

        row = layout.row()
        row.operator("alm.grease_to_curve", text='Drop to Curve')

        row = layout.row()
        row.operator("alm.curve_to_mesh", text='Curve to Mesh')

        row = layout.row()
        row.operator("alm.view_locker", text='Lock View')

classes = [ViewLocker, SketchOperator, CurveOperator, MeshOperator, AddonPanel]

def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
