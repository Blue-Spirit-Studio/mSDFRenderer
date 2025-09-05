"""
File:           sdf_setting_node.py

Description:    Maya Node plugin to manage shaders parameters in real time

Author:         Pierre Vandel
"""

import maya.api.OpenMaya as om
import sys

def maya_useNewAPI():
    """
    Use the Maya Python API 2.0.
    """
    pass

class SDFSettingNode(om.MPxNode):
    """
    Creation of Custom Maya node
    """
    # Node name
    kNodeName = "SDFSettingNode"
    # Node ID
    kTypeId = om.MTypeId(0x84019)
    # Color attribute
    a_color = om.MObject()
    # Render type attribute
    a_render_type = om.MObject()

    def __init__(self):
        om.MPxNode.__init__(self)

    @staticmethod
    def nodeCreator():
        return SDFSettingNode()

    @staticmethod
    def nodeInitializer():
        # Color attribute
        fn_color_attr = om.MFnNumericAttribute()
        SDFSettingNode.a_color = fn_color_attr.createColor("color", "clr")
        fn_color_attr.default = (0.18, 0.18, 0.18)  # Default to grey
        fn_color_attr.keyable = True
        SDFSettingNode.addAttribute(SDFSettingNode.a_color)

        fn_render_type_attr = om.MFnEnumAttribute()
        SDFSettingNode.a_render_type = fn_render_type_attr.create("renderType", "rdt")
        fn_render_type_attr.addField("Lambert", 0)
        fn_render_type_attr.addField("Realistic", 1)

        fn_render_type_attr.default = 0
        fn_color_attr.keyable = True
        fn_color_attr.readable = True
        fn_color_attr.writable = True
        fn_color_attr.storable = True
        SDFSettingNode.addAttribute(SDFSettingNode.a_render_type)


def initializePlugin(mobject):
    mplugin = om.MFnPlugin(mobject)
    try:
        mplugin.registerNode(SDFSettingNode.kNodeName,
                             SDFSettingNode.kTypeId,
                             SDFSettingNode.nodeCreator,
                             SDFSettingNode.nodeInitializer,
                             om.MPxNode.kDependNode)
    except:
        sys.stderr.write("Failed to register node: {}".format(SDFSettingNode.kNodeName))
        raise


def uninitializePlugin(mobject):
    mplugin = om.MFnPlugin(mobject)
    try:
        mplugin.deregisterNode(SDFSettingNode.kTypeId)
    except:
        sys.stderr.write("Failed to deregister node: {}".format(SDFSettingNode.kNodeName))
        raise
