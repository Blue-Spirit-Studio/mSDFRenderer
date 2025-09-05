"""
File:           sdf_render.py

Description:    SDF Renderer plugin for Maya which override Maya viewport to
                display SDF

Author:         Pierre Vandel
"""

from builtins import range
import sys

import maya.api.OpenMayaRender as omr
import maya.api.OpenMayaUI as omui
import maya.api.OpenMaya as om

import api

# Please fill those paths with wanted shader and grid location
SHADER_PATH = r""
GRID_PATH = r""  # Optional


def maya_useNewAPI():
    """
    use the Maya Python API 2.0.
    """
    pass


# Enumerations to identify an operation within a list of operations.
kBackground = 1
kMaya3dSceneRender = 2  # 3d scene render to target 1
kMaya3dSceneRenderUI = 3  # Post ui draw to target 1
kSDFQuadRender = 4
kHUDBlit = 5  # Draw HUD on top

kPresentOp = 6  # Present
kNumberOfOps = 7

# Helper to enumerate the target indexing
kMyColorTarget = 0  # color target
kMyDepthTarget = 1  # depth target
kTargetCount = 2


class ViewRenderHUDOperation(omr.MHUDRender):
    """
    Override of MHUDRender from OpenMayaRender
    Custom HUD Operations
    Add UI elements on top of the render view.
    """
    def __init__(self):
        omr.MHUDRender.__init__(self)

        self.m_targets = None

    # Target override
    def targetOverrideList(self):
        if not self.m_targets is None:
            return [self.m_targets[kMyColorTarget], self.m_targets[kMyDepthTarget]]
        return None

    def hasUIDrawables(self):
        return True

    def addUIDrawables(self, draw_manager_2d, frame_context):

        draw_manager_2d.beginDrawable()
        # Set font color
        draw_manager_2d.setColor(om.MColor((1.0, 1.0, 1.0)))
        # Set font size
        draw_manager_2d.setFontSize(omr.MUIDrawManager.kSmallFontSize)
        draw_manager_2d.setFontSize(25)
        # Draw renderer name
        dim = frame_context.getViewportDimensions()
        x = dim[0]
        y = dim[1]
        w = dim[2]
        h = dim[3]
        draw_manager_2d.text(om.MPoint(w * 0.5, h * 0.91), "SDF Renderer Override debug", omr.MUIDrawManager.kCenter)

        draw_manager_2d.endDrawable()

    def setRenderTargets(self, targets):
        self.m_targets = targets


class ViewRenderPresentTarget(omr.MPresentTarget):
    """
    Override of MPresentTarget from OpenMayaRender
    Custom present target operation
    Only overrides the targets to present.
    """
    def __init__(self, name):
        omr.MPresentTarget.__init__(self, name)
        # Targets used as input parameters to mShaderInstance
        self.m_targets = None

    def targetOverrideList(self):
        if not self.m_targets is None:
            return [self.m_targets[kMyColorTarget], self.m_targets[kMyDepthTarget]]
        return None

    def setRenderTargets(self, targets):
        self.m_targets = targets


class SDFRenderOverride(omr.MRenderOverride):
    """
    Override of MRenderOverride from OpenMayaRender
    Allows users to fully custom the render process within the Maya viewport.
    It offers the possibility to define a custom render flow.
    This class is called when the plugin is loaded
    """

    def __init__(self, name):

        omr.MRenderOverride.__init__(self, name)

        self.m_ui_name = "SDF Renderer"

        # Operation lists
        self.m_render_operations = []
        self.m_render_operations_names = []

        for i in range(kNumberOfOps):
            self.m_render_operations.append(None)
            self.m_render_operations_names.append("")
        self.m_current_operation = -1

        # Shared render target list
        self.m_target_override_names = []
        self.m_target_descriptions = []
        self.m_targets = []
        self.m_target_supports_srgb_write = []

        for i in range(kTargetCount):
            self.m_target_override_names.append("")
            self.m_target_descriptions.append(None)
            self.m_targets.append(None)
            self.m_target_supports_srgb_write.append(False)

        # Init target information for the override
        sample_count = 1  # no multi-sampling
        color_format = omr.MRenderer.kR8G8B8A8_UNORM
        depth_format = omr.MRenderer.kD24S8

        # 2 render targets used for the entire override
        self.m_target_override_names[kMyColorTarget] = "__SDFRenderOverrideCustomColorTarget__"
        self.m_target_descriptions[kMyColorTarget] = omr.MRenderTargetDescription(
            self.m_target_override_names[kMyColorTarget], 256, 256, sample_count, color_format, 0, False)
        self.m_targets[kMyColorTarget] = None
        self.m_target_supports_srgb_write[kMyColorTarget] = False

        self.m_target_override_names[kMyDepthTarget] = "__SDFRenderOverrideCustomDepthTarget__"
        self.m_target_descriptions[kMyDepthTarget] = omr.MRenderTargetDescription(
            self.m_target_override_names[kMyDepthTarget], 256, 256, sample_count, depth_format, 0, False)
        self.m_targets[kMyDepthTarget] = None
        self.m_target_supports_srgb_write[kMyDepthTarget] = False

        # For debugging
        self.m_debug_override = False

        # Override is for this panel
        self.m_panel_name = ""

    def __del__(self):
        target_manager = omr.MRenderer.getRenderTargetManager()

        # Delete any targets created
        for i in range(kTargetCount):
            self.m_target_descriptions[i] = None

            if not self.m_targets[i] is None:
                if not target_manager is None:
                    target_manager.releaseRenderTarget(self.m_targets[i])
                self.m_targets[i] = None

        self.cleanup()

        # Delete all the operations. This will release any references to other resources used per operation
        for i in range(kNumberOfOps):
            self.m_render_operations[i] = None

    def supportedDrawAPIs(self):
        """
        Return that this plugin supports both GL and DX draw APIs
        """
        return omr.MRenderer.kOpenGL | omr.MRenderer.kDirectX11 | omr.MRenderer.kOpenGLCoreProfile

    def startOperationIterator(self):
        """
        Initialize "iterator". Keep a list of operations indexed
        by mCurrentOperation. Set to 0 to point to the first operation.
        """
        self.m_current_operation = 0
        return True

    def renderOperation(self):
        """
        Return an operation indicated by mCurrentOperation
        """
        if 0 <= self.m_current_operation < kNumberOfOps:
            while self.m_render_operations[self.m_current_operation] is None:
                self.m_current_operation = self.m_current_operation + 1
                if self.m_current_operation >= kNumberOfOps:
                    return None

            if not self.m_render_operations[self.m_current_operation] is None:
                if self.m_debug_override:
                    print("\t" + self.name() + "Queue render operation[" + str(self.m_current_operation) + "] = (" +
                          self.m_render_operations[self.m_current_operation].name() + ")")
                return self.m_render_operations[self.m_current_operation]
        return None

    def nextRenderOperation(self):
        self.m_current_operation = self.m_current_operation + 1
        if self.m_current_operation < kNumberOfOps:
            return True
        return False

    def update_render_targets(self):
        """
        Get the current output target size as specified by the
        renderer. If it has changed then the targets need to be
        resized to match.
        """

        targetSize = omr.MRenderer.outputTargetSize()
        targetWidth = targetSize[0]
        targetHeight = targetSize[1]

        # Note that the render target sizes could be set to be
        # smaller than the size used by the renderer. In this case
        # a final present will generally stretch the output.

        # Update size value for all target descriptions kept
        for targetId in range(kTargetCount):
            self.m_target_descriptions[targetId].setWidth(targetWidth)
            self.m_target_descriptions[targetId].setHeight(targetHeight)

        # Keep track of whether the main color target can support sRGB write
        colorTargetSupportsSGRBWrite = False
        # Uncomment this to debug if targets support sRGB write.
        sDebugSRGBWrite = False
        # Enable to test unordered write access
        testUnorderedWriteAccess = False

        # Either acquire a new target if it didn't exist before, resize
        # the current target.
        targetManager = omr.MRenderer.getRenderTargetManager()
        if not targetManager is None:
            if sDebugSRGBWrite:
                if omr.MRenderer.drawAPI() != omr.MRenderer.kOpenGL:
                    # scan all available target for sRGB write support
                    for i in range(omr.MRenderer.kNumberOfRasterFormats):
                        if targetManager.formatSupportsSRGBWrite(i):
                            print("Format " + str(i) + " supports SRGBwrite")

            for targetId in range(kTargetCount):
                # Check to see if the format supports sRGB write.
                # Set unordered write access flag if test enabled.
                supportsSRGBWrite = False
                if omr.MRenderer.drawAPI() != omr.MRenderer.kOpenGL:
                    supportsSRGBWrite = targetManager.formatSupportsSRGBWrite(
                        self.m_target_descriptions[targetId].rasterFormat())
                    self.m_target_supports_srgb_write[targetId] = supportsSRGBWrite
                self.m_target_descriptions[targetId].setAllowsUnorderedAccess(testUnorderedWriteAccess)

                # Keep track of whether the main color target can support sRGB write
                if targetId == kMyColorTarget:
                    colorTargetSupportsSGRBWrite = supportsSRGBWrite

                if sDebugSRGBWrite:
                    if targetId == kMyColorTarget:
                        print("Color target " + str(targetId) + " supports sRGB write = " + str(supportsSRGBWrite))
                    # This would be expected to fail.
                    if targetId == kMyDepthTarget:
                        print("Depth target supports sRGB write = " + str(supportsSRGBWrite))

                # Create a new target
                if self.m_targets[targetId] is None:
                    self.m_targets[targetId] = targetManager.acquireRenderTarget(self.m_target_descriptions[targetId])

                # "Update" using a description will resize as necessary
                else:
                    self.m_targets[targetId].updateDescription(self.m_target_descriptions[targetId])

                if testUnorderedWriteAccess and not self.m_targets[targetId] is None:
                    returnDesc = self.m_targets[targetId].targetDescription()
                    self.m_target_descriptions[targetId].setAllowsUnorderedAccess(returnDesc.allowsUnorderedAccess())
                    print("Acquire target[" + returnDesc.name() + "] with unordered access = " + str(
                        returnDesc.allowsUnorderedAccess()) + ". Should fail if attempting with depth target = " + str(
                        targetId == kMyDepthTarget))

        # Update the render targets on the individual operations
        #
        # Set the targets on the operations. For simplicity just
        # passing over the set of all targets used for the frame
        # to each operation.
        quadOp = self.m_render_operations[kBackground]
        if not quadOp is None:
            quadOp.setRenderTargets(self.m_targets)

        sceneOp = self.m_render_operations[kMaya3dSceneRender]
        if not sceneOp is None:
            sceneOp.setRenderTargets(self.m_targets)
            sceneOp.setEnableSRGBWriteFlag(colorTargetSupportsSGRBWrite)

        uiSceneOp = self.m_render_operations[kMaya3dSceneRenderUI]
        if not uiSceneOp is None:
            uiSceneOp.setRenderTargets(self.m_targets)
            uiSceneOp.setEnableSRGBWriteFlag(False)  # Don't enable sRGB write for UI

        presentOp = self.m_render_operations[kPresentOp]
        if not presentOp is None:
            presentOp.setRenderTargets(self.m_targets)

        hudOp = self.m_render_operations[kHUDBlit]
        if not hudOp is None:
            hudOp.setRenderTargets(self.m_targets)

        sdfDisplayOp = self.m_render_operations[kSDFQuadRender]
        if not sdfDisplayOp is None:
            sdfDisplayOp.setRenderTargets(self.m_targets)

        return (not self.m_targets[kMyColorTarget] is None and not self.m_targets[kMyDepthTarget] is None)

    # setup will be called for each frame update.

    def setup(self, destination):

        # keep track of the active 3d viewport panel
        # if any exists. This information is passed to the operations
        # in case they require accessing the current 3d view (M3dView).
        self.m_panel_name = destination  # modelPanel
        rect = om.MFloatPoint(0.0, 0.0, 1.0, 1.0)

        if self.m_render_operations[kPresentOp] is None:

            # Maya scene render operation

            clearMask = omr.MClearOperation.kClearDepth | omr.MClearOperation.kClearStencil
            self.m_render_operations_names[kMaya3dSceneRender] = "__OverrideSceneRender"
            scene_op = viewRenderSceneRender(self.m_render_operations_names[kMaya3dSceneRender],
                                             omr.MSceneRender.kNoSceneFilterOverride, clearMask)

            scene_op.setViewRectangle(rect)
            self.m_render_operations[kMaya3dSceneRender] = scene_op

            # SDF quad render operation

            sdf_quad_render_op = viewRenderQuadRender(self.m_render_operations_names[kSDFQuadRender])
            self.m_render_operations[kSDFQuadRender] = sdf_quad_render_op

            self.m_render_operations[kMaya3dSceneRenderUI] = None

            self.m_render_operations_names[kPresentOp] = "__MyPresentTarget"

            self.m_render_operations[kPresentOp] = ViewRenderPresentTarget(self.m_render_operations_names[kPresentOp])
            self.m_render_operations_names[kPresentOp] = self.m_render_operations[kPresentOp].name()

            # A preset 2D HUD render operation

            self.m_render_operations[kHUDBlit] = ViewRenderHUDOperation()
            self.m_render_operations_names[kHUDBlit] = self.m_render_operations[kHUDBlit].name()

        got_targets = self.update_render_targets()
        self.m_current_operation = -1

        if not got_targets:
            raise ValueError

    def panelName(self):
        return self.m_panel_name

    def uiName(self):
        return self.m_ui_name


class viewRenderQuadRender(omr.MQuadRender):
    """
    Override of MQuadRender from OpenMayaRender
    Operation used for post effect treatment, specific treatment for final
    render.
    It consists of the creation of a quad in screen space.
    It's during this operation that the shader instance is created and all the
    data is transfer to it thanks to
    MRenderTarget.
    """

    def __init__(self, name):
        omr.MQuadRender.__init__(self, name)

        # Shader to use for the quad render
        self.mShaderInstance = None
        # Targets used as input parameters to mShaderInstance
        self.m_targets = None
        # View rectangle
        self.mViewRectangle = om.MFloatPoint()
        # Shader to use for quad rendering
        self.mShader = None

    def __del__(self):
        if not self.mShaderInstance is None:
            shaderMgr = omr.MRenderer.getShaderManager()
            if not shaderMgr is None:
                shaderMgr.releaseShader(self.mShaderInstance)
            self.mShaderInstance = None

    def shader(self):
        """
        Return the appropriate shader instance based on what we want the quad
        operation to perform
        """
        # Create a new shader instance for this quad render instance
        if self.mShaderInstance is None:
            shaderMgr = omr.MRenderer.getShaderManager()
            self.mShaderInstance = shaderMgr.getEffectsFileShader(SHADER_PATH, "" )

        # Set parameters on the shader instance.
        # This is where the input render targets can be specified by binding
        # a render target to the appropriate parameter on the shader instance.
        if not self.mShaderInstance is None:

            try:
                # Set input render target / texture parameter on shader
                self.mShaderInstance.setParameter("gInputTex", self.m_targets[kMyColorTarget])
            except Exception as e:
                print("Could not set input render target / texture parameter on shader"), e

            try:
                # Set input render target / depth parameter on shader
                self.mShaderInstance.setParameter("gInputDepth", self.m_targets[kMyDepthTarget])
            except Exception as e:
                print("Could not set input render target / depth parameter on shader"), e

            try:
                textureMgr = omr.MRenderer.getTextureManager()
                mTexture = textureMgr.acquireTexture(GRID_PATH)
                self.mShaderInstance.setParameter("gInputGrid", mTexture)
            except Exception as e:
                print("Could not set input grid parameter on shader"), e

            # Set sdf surface color
            try:
                color_r, color_g, color_b = api.get_color()
                self.mShaderInstance.setParameter("colorR", color_r)
                self.mShaderInstance.setParameter("colorG", color_g)
                self.mShaderInstance.setParameter("colorB", color_b)
            except:
                print("Warning : There is no uniform called 'colorR', 'colorG' and 'colorB' in the shader")

            # Set render type
            try:
                render_type = api.get_render_type()
                self.mShaderInstance.setParameter("renderType", render_type)
            except:
                print("Warning : The is no uniform called 'renderType' in the shader'")

            # Set camera translation to shader
            try:
                cam_pos_x, cam_pos_y, cam_pos_z = api.get_cam_translate()
                self.mShaderInstance.setParameter("camPosX", cam_pos_x)
                self.mShaderInstance.setParameter("camPosY", cam_pos_y)
                self.mShaderInstance.setParameter("camPosZ", cam_pos_z)
            except:
                print("Warning : There is no uniform called 'camPosX', 'camPosY' and 'camPosZ' in the shader")

            # Set camera rotation to shader
            try:
                cam_rot_x, cam_rot_y, cam_rot_z = api.get_cam_rotate()
                self.mShaderInstance.setParameter("camRotX", cam_rot_x)
                self.mShaderInstance.setParameter("camRotY", cam_rot_y)
                self.mShaderInstance.setParameter("camRotZ", cam_rot_z)
            except:
                print("Warning : There is no uniform called 'camRotX', 'camRotY' and 'camRotZ' in the shader")

            # Set active viewport aspect ratio to shader
            try:
                self.mShaderInstance.setParameter("aspectRatio", api.get_aspect_ratio())
            except:
                print("Warning : There is no uniform called 'aspectRatio' in the shader")

            # Set the fov of the camera to shader
            try:
                fovV_deg, fovH_deg = api.get_cam_fov()
                self.mShaderInstance.setParameter("fovV", fovV_deg)
                self.mShaderInstance.setParameter("fovH", fovH_deg)
            except:
                print("Warning : There is no uniform called 'fovV' or 'fovH' in the shader")

            # Set current frame to shader
            try:
                self.mShaderInstance.setParameter("frame", api.get_current_frame())
            except:
                print("Warning : There is no uniform called 'frame' in the shader")

            # Set camera clipping to shader
            try:
                near_clip, far_clip = api.get_cam_clipping()
                self.mShaderInstance.setParameter("nearClip", near_clip)
                self.mShaderInstance.setParameter("farClip", far_clip)
            except:
                print("Warning : There is no uniform called 'nearClip' or farClip in the shader")

        return self.mShaderInstance

    def targetOverrideList(self):
        if not self.m_targets is None:
            return [self.m_targets[kMyColorTarget], self.m_targets[kMyDepthTarget]]
        return None

    # Set the clear override to use.
    def clearOperation(self):
        clearOp = self.mClearOperation
        clearOp.setClearGradient(False)
        clearOp.setMask(omr.MClearOperation.kClearNone)
        return clearOp

    def setRenderTargets(self, targets):
        self.m_targets = targets

    def setShader(self, shader):
        self.mShader = shader

    def viewRectangle(self):
        return self.mViewRectangle

    def setViewRectangle(self, rect):
        self.mViewRectangle = rect


class viewRenderSceneRender(omr.MSceneRender):

    """
    Override of MSceneRender from OpenMayaRender
    Render operation which manage display of the scene 3D content. It allows the
    drawing of 3D objects in
    the viewport based on camera parameter such as lights, shadows and other.
    """

    def __init__(self, name, sceneFilter, clearMask):
        omr.MSceneRender.__init__(self, name)

        self.mSelectionList = om.MSelectionList()

        # 3D viewport panel name, if available
        self.mPanelName = ""
        # Camera override
        self.mCameraOverride = omr.MCameraOverride()
        # Viewport rectangle override
        self.mViewRectangle = om.MFloatPoint(0.0, 0.0, 1.0, 1.0)  # 100 % of target size
        # Available render targets
        self.m_targets = None
        # Shader override for surfaces
        self.mShaderOverride = None
        # Scene draw filter override
        self.mSceneFilter = sceneFilter
        # Mask for clear override
        self.mClearMask = clearMask

        # Some sample override flags
        self.mUseShaderOverride = False
        self.mUseStockShaderOverride = False
        self.mAttachPrePostShaderCallback = False
        self.mUseShadowShader = False
        self.mOverrideDisplayMode = True
        self.mOverrideLightingMode = False
        self.mOverrideCullingMode = False
        self.mDebugTargetResourceHandle = False
        self.mOverrrideM3dViewDisplayMode = False
        self.mPrevDisplayStyle = omui.M3dView.kGouraudShaded  # Track previous display style of override set
        self.mFilterDrawNothing = False
        self.mFilterDrawSelected = True
        self.mEnableSRGBWrite = False

    def __del__(self):
        if not self.mShaderOverride is None:
            shaderMgr = omr.MRenderer.getShaderManager()
            if not shaderMgr is None:
                shaderMgr.releaseShader(self.mShaderOverride)
            self.mShaderOverride = None

    def setRenderTargets(self, targets):
        self.m_targets = targets

    def targetOverrideList(self):
        if not self.m_targets is None:
            return [self.m_targets[kMyColorTarget], self.m_targets[kMyDepthTarget]]
        return None

    def enableSRGBWrite(self):
        """
        Indicate whether to enable SRGB write.
        """
        return self.mEnableSRGBWrite

    def cullingOverride(self):
        """
        cull backfacing polygons.
        """
        if self.mOverrideCullingMode:
            return omr.MSceneRender.kCullBackFaces
        return omr.MSceneRender.kNoCullingOverride

    def clearOperation(self):
        """
        Custom clear override.
        Depending on whether we are drawing the "UI" or "non-UI"
        parts of the scene we will clear different channels.
        Color is never cleared since there is a separate operation
        to clear the background.
        """
        pass

    def panelName(self):
        return self.mPanelName

    def viewRectangle(self):
        return self.mViewRectangle

    def setViewRectangle(self, rect):
        self.mViewRectangle = rect

    def colorTarget(self):
        if not self.m_targets is None:
            return self.m_targets[kMyColorTarget]
        return None

    def depthTarget(self):
        if not self.m_targets is None:
            return self.m_targets[kMyDepthTarget]
        return None

    def setEnableSRGBWriteFlag(self, val):
        self.mEnableSRGBWrite = val

    def enableSRGBWriteFlag(self):
        return self.mEnableSRGBWrite

    def objectSetOverride(self):
        self.mSelectionList.clear()

        # If you set this to True you can make the
        # scene draw no part of the scene, only the
        # additional UI elements
        if self.mFilterDrawNothing:
            return self.mSelectionList

        # Turn this on to query the active list and only
        # use that for drawing
        if self.mFilterDrawSelected:
            selList = om.MGlobal.getActiveSelectionList()
            if selList.length() > 0:
                iter = om.MItSelectionList(selList)
                while not iter.isDone():
                    #comp = iter.getComponent()
                    #for c in comp:
                    #    self.mSelectionList.add(c)
                    next(iter)

            if self.mSelectionList.length() > 0:
                print("\t" + self.name() + " : Filtering render with active object list")
                return self.mSelectionList
        return None


sdf_render_override_instance = None


def initializePlugin(obj):
    plugin = om.MFnPlugin(obj)
    try:
        global sdf_render_override_instance
        sdf_render_override_instance = SDFRenderOverride("SDFRenderOverride")
        omr.MRenderer.registerOverride(sdf_render_override_instance)
    except:
        sys.stderr.write("registerOverride\n")
        raise


def uninitializePlugin(obj):
    plugin = om.MFnPlugin(obj)
    try:
        global sdf_render_override_instance
        if not sdf_render_override_instance is None:
            omr.MRenderer.deregisterOverride(sdf_render_override_instance)
            sdf_render_override_instance = None
    except:
        sys.stderr.write("deregisterOverride\n")
        raise
