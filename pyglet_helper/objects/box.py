from pyglet.gl import *
from pyglet_helper.objects import Rectangular
from pyglet_helper.util import Rgb, Vector


class Box(Rectangular):
    """
     A box object.
    """
    def __init__(self, width=1.0, height=1.0, length=1.0, color=Rgb(), pos=Vector(0, 0, 0)):
        super(Box, self).__init__(width=width, height=height, color=color, length=length, pos=pos)

    # True if the box should not be rendered.
    def init_model(self, scene, skip_right_face=False):
        # Note that this model is also used by arrow!
        scene.box_model.gl_compile_begin()
        glEnable(GL_CULL_FACE)
        glBegin(GL_TRIANGLES)

        s = 0.5
        vertices = [
            [[+s, +s, +s], [+s, -s, +s], [+s, -s, -s], [+s, +s, -s]],  # Right face
            [[-s, +s, -s], [-s, -s, -s], [-s, -s, +s], [-s, +s, +s]],  # Left face
            [[-s, -s, +s], [-s, -s, -s], [+s, -s, -s], [+s, -s, +s]],  # Bottom face
            [[-s, +s, -s], [-s, +s, +s], [+s, +s, +s], [+s, +s, -s]],  # Top face
            [[+s, +s, +s], [-s, +s, +s], [-s, -s, +s], [+s, -s, +s]],  # Front face
            [[-s, -s, -s], [-s, +s, -s], [+s, +s, -s], [+s, -s, -s]]  # Back face
        ]
        normals = [[+1, 0, 0], [-1, 0, 0], [0, -1, 0], [0, +1, 0], [0, 0, +1], [0, 0, -1]]
        # Draw inside (reverse winding and normals)
        for f in range(skip_right_face, 6):
            glNormal3f(-normals[f][0], -normals[f][1], -normals[f][2])
            for v in range(0, 3):
                glVertex3f(GLfloat(vertices[f][3 - v][0]), GLfloat(vertices[f][3 - v][1]),
                           GLfloat(vertices[f][3 - v][2]))
            for v in (0, 2, 3):
                glVertex3f(GLfloat(vertices[f][3 - v][0]), GLfloat(vertices[f][3 - v][1]),
                           GLfloat(vertices[f][3 - v][2]))
        # Draw outside
        for f in range(skip_right_face, 6):
            glNormal3f(GLfloat(normals[f][0]), GLfloat(normals[f][1]), GLfloat(normals[f][2]))
            for v in range(0, 3):
                glVertex3f(GLfloat(vertices[f][v][0]), GLfloat(vertices[f][v][1]), GLfloat(vertices[f][v][2]))
            for v in (0, 2, 3):
                glVertex3f(GLfloat(vertices[f][v][0]), GLfloat(vertices[f][v][1]), GLfloat(vertices[f][v][2]))
        glEnd()
        glDisable(GL_CULL_FACE)
        scene.box_model.gl_compile_end()

    def gl_pick_render(self, scene):
        self.render(scene)

    def render(self, scene):
        if not scene.box_model.compiled:
            self.init_model(scene, False)
        self.color.gl_set(self.opacity)
        glPushMatrix()
        self.apply_transform(scene)
        scene.box_model.gl_render()
        glPopMatrix()

    def grow_extent(self, e):
        tm = self.model_world_transform(1.0, Vector(self.axis.mag(), self.height, self.width) * 0.5)
        e.add_box(tm, Vector(-1, -1, -1), Vector(1, 1, 1))
        e.add_body()
        return e

    def get_material_matrix(self, out):
        out.translate(Vector(.5, .5, .5))
        scale = Vector(self.axis.mag(), self.height, self.width)
        out.scale(scale * (1.0 / max(scale.x, max(scale.y, scale.z))))
        return out