"""
File        : api.py
Description : API to get all the data from the Maya scene
"""

import maya.api.OpenMayaUI as omui
import maya.cmds as mc
import math

from sdf_setting_node import SDFSettingNode


def get_aspect_ratio():
    """
    Get the aspect ratio of the current viewport
    :return: aspect ratio
    :rtype: float
    """
    view = omui.M3dView.active3dView()
    w = view.portWidth()
    h = view.portHeight()
    if h == 0:
        aspect_ratio = float(1.0)
    else:
        aspect_ratio = float(w) / float(h)

    return aspect_ratio


def get_cam_fov(cam="persp"):
    """
    Get the field of view of the given camera
    :param cam: name of the camera we want the fov from
    :return: vertical and horizontal fov in degrees
    :rtype: tuple(float, float)
    """
    cam_shape = mc.listRelatives(cam, shapes=True)[0]
    focal_length = mc.getAttr("{}.focalLength".format(cam_shape))
    vertical_aperture = mc.getAttr("{}.verticalFilmAperture".format(cam_shape))
    vertical_aperture = vertical_aperture * 25.4

    # Calculate vertical fov in radians
    vertical_fov_rad = 2 * math.atan((vertical_aperture / 2) / focal_length)
    # Calculate vertical fov in degrees
    vertical_fov_deg = math.degrees(vertical_fov_rad)

    aspect_ratio = get_aspect_ratio()
    # Calculate horizontal fov in radians
    horizontal_fov_rad = 2 * math.atan(math.tan(vertical_fov_rad / 2) * aspect_ratio)
    # Calculate horizontal fov in degrees
    horizontal_fov_deg = math.degrees(horizontal_fov_rad)

    return vertical_fov_deg, horizontal_fov_deg


def get_current_frame(offset=1000):
    """
    Get the current frame of the current scene
    :param offset: offset
    :type offset: int
    :return: current frame
    :rtype: int
    """
    current_frame = mc.currentTime(q=True)
    return current_frame - offset


def get_color():
    """
    Get the color specified in sdf setting node
    :return: color
    :rtype: tuple(float, float, float)
    """
    sdf_setting_node_name = get_setting_node()
    color_r, color_g, color_b = mc.getAttr("{}.color".format(sdf_setting_node_name))[0]
    return color_r, color_g, color_b


def get_render_type():
    """
    Get the render type specified in sdf setting node
    :return: render type
    :rtype: int
    """
    sdf_setting_node_name = get_setting_node()
    render_type = mc.getAttr("{}.renderType".format(sdf_setting_node_name))
    return render_type


def get_cam_translate(cam="persp"):
    """
    Get the position of the given camera.
    :param cam: Name of the camera we want the position from
    :type cam : str
    :return: camera positions
    :rtype: tuple(float, float, float)
    """
    return mc.getAttr("{}.translate".format(cam))[0]


def get_cam_rotate(cam="persp"):
    """
    Get the rotation of the given camera.
    :param cam: Name of the camera we want the rotation from
    :type cam : str
    :return: camera rotation
    :rtype: tuple(float, float, float)
    """
    return mc.getAttr("{}.rotate".format(cam))[0]


def get_cam_clipping(cam="persp"):
    """
    Get the clipping of the given camera.
    :param cam: camera name we want the clipping from
    :type cam: str
    :return: near clip and far clip
    :rtype: tuple(float, float)
    """
    near_clip = mc.getAttr("{}.nearClipPlane".format(cam))
    far_clip = mc.getAttr("{}.farClipPlane".format(cam))
    return near_clip, far_clip


def get_setting_node():
    """
    Get the setting node
    :return: setting node name
    :rtype: str
    """
    return mc.ls(type=SDFSettingNode.kNodeName)[0]

