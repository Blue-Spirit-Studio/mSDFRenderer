"""
File:           gen_sdf.py

Description:    Script to generate an SDF from a given mesh (.obj). The SDF is
                stored into a 3D signed distance grid, where each cell of the
                grid contains his distance with the closest mesh surface.
                To be easily readable by the shader, this grid is flatten into a
                2D texture (.png). A technique where multiple smaller images are
                combined into a single larger image called an atlas.

Author:         Pierre Vandel
"""


import os
import sys
import trimesh
import mesh2sdf
import numpy as np
import imageio


def get_mesh(filename):
    """
    Get the mesh from a file
    :param filename: file path name
    :type filename: str
    :return: Loaded geometry as trimesh classes
    :rtype: Geometry
    """
    mesh = trimesh.load(filename, force='mesh')
    return mesh


def get_sdf(mesh, mesh_scale, size, level):
    """
    Compute SDF from a given mesh. For each cell of the grid, it stores
    the closed distance 
    :param mesh: Mesh
    :type mesh: Geometry
    :param mesh_scale: Scale factor for the mesh size inside the grid
    :type mesh_scale: float
    :param size: Grid size (the resolution of the resulting SDF). Higher the
    size is, better the quality is.
    :type size: int
    :param level: The value used to extract level sets
    :type level: float
    :return: 3D grid which contains all signed distance
    :rtype: numpy.ndarray[numpy.float32]
    """
    # normalize mesh
    vertices = mesh.vertices
    bbmin = vertices.min(0)
    bbmax = vertices.max(0)
    center = (bbmin + bbmax) * 0.5

    scale = 2.0 * mesh_scale / (bbmax - bbmin).max()
    vertices = (vertices - center) * scale

    # Compute SDF from mesh
    sdf, fixed_mesh = mesh2sdf.compute(
        vertices, mesh.faces, size, fix=True, level=level, return_mesh=True)

    return sdf


def get_atlas(sdf_grid):
    """
    Convert a 3D grid into a 2D texture
    :param sdf_grid: 3D signed distance grid
    :type sdf_grid: numpy.ndarray[numpy.float32]
    :return: atlas, 3D grid flatten into 2D texture
    :rtype: numpy.ndarray
    """
    # grid: shape (depth, height, width)
    D, H, W = sdf_grid.shape
    atlas = np.zeros((D * H, W), dtype=np.float32)
    for z in range(D):
        atlas[z*H:(z+1)*H, :] = sdf_grid[z]

    # Normalization, converts signed distance values into grey level to be store
    # in the image
    atlas_norm = ((atlas - atlas.min()) / (atlas.ptp() + 1e-8) * 255).astype(np.uint8)
    return atlas_norm


def main():

    # Get arguments
    input_file = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(os.path.dirname(__file__), 'data', 'stanford-bunny.obj')
    output_file = sys.argv[2] if len(sys.argv) > 2 else \
        os.path.join(os.path.dirname(__file__), 'data', 'grille_atlas.png')
    size = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    mesh_scale = float(sys.argv[4]) if len(sys.argv) > 4 else 0.8

    level = 2 / size

    # Start the converting process
    mesh = get_mesh(input_file)
    sdf = get_sdf(mesh, mesh_scale, size, level)
    atlas = get_atlas(sdf)

    imageio.imwrite(output_file, atlas)


main()
