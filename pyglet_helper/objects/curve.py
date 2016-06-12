try:
    from pyglet.gl import gl
except Exception as error_msg:
    gl = None

from pyglet_helper.objects import ArrayPrimitive
from pyglet_helper.util import Rgb, Vector, make_pointer
from math import pi, cos, sin
from numpy import zeros
from ctypes import sizeof, c_uint, c_int, byref




class Curve(ArrayPrimitive):
    def __init__(self, color=Rgb(), antialias=True, radius=0.0, sides=4):
        super(Curve, self).__init__()
        # since wxPython is not being used, the frame argument is not important for now
        self.antialias = antialias
        self.radius = radius
        self.sides = sides
        self.curve_sc = zeros(sides*2)
        self.curve_slice = zeros(128*2+257)
        for i in range(0, sides):
            self.curve_sc[i] = cos(i * 2 * pi / sides)
            self.curve_sc[i+sides] = sin(i * 2 * pi / sides)

        # curve_slice is a list of indices for picking out the correct vertices from
        # a list of vertices representing one side of a thick-line curve. The lower
        # indices (0-255) are used for all but one of the sides. The upper indices
        # (256-511) are used for the final side.
        for i in range(0, 128):
            self.curve_slice[i*2]       = i*sides
            self.curve_slice[i*2+1]     = i*sides + 1
            self.curve_slice[i*2 + 256] = i*sides + (sides - 1)
            self.curve_slice[i*2 + 257] = i*sides

    @property
    def degenerate(self):
        return self.count < 2

    def monochrome(self):
        """
        Checks whether all colors in a list are the same
        :param tcolor: the list of colors
        :type tcolor: list
        :param pcount: the number of colors in the ArrayPrimitive to check
        :type pcount: int
        :return: boolean, either True if all colors are the same, false otherwise
        :rtype: boolean
        """
        first_color = self.color[0]
        for nn in range(0, self.count):
            if self.color[nn] != first_color:
                return False
        return True

    def render(self, scene):
        if self.degenerate:
            return
        # Set up the leading and trailing points for the joins.  See
        # glePolyCylinder() for details.  The intent is to create joins that are
        # perpendicular to the path at the last segment.  When the path appears
        # to be closed, it should be rendered that way on-screen.
        # The maximum number of points to display.
        line_length = 1000
        # yet implemented for curves
        iptr = 0


        # Do scaling if necessary
        scaled_radius = self.radius
        if scene.gcf != 1.0 or scene.gcfvec[0] != scene.gcfvec[1]:
            scaled_radius = self.radius*scene.gcfvec[0]
            for i in range(0, self.count):
                self.pos[i] *= scene.gcfvec

        if self.radius == 0.0:
            gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
            gl.glDisable(gl.GL_LIGHTING)
            # Assume monochrome.
            if self.antialias:
                gl.glEnable(gl.GL_LINE_SMOOTH)

            gl.glVertexPointer(3, gl.GL_DOUBLE, 0, self.pos)
            mono = self.adjust_colors(scene)
            if not mono:
                gl.glColorPointer(3, gl.GL_FLOAT, 0, self.color)
            gl.glDrawArrays(gl.GL_LINE_STRIP, 0, self.pos)
            gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
            gl.glDisableClientState(gl.GL_COLOR_ARRAY)
            gl.glEnable(gl.GL_LIGHTING)
            if self.antialias:
                gl.glDisable(gl.GL_LINE_SMOOTH)
        else:
            self.thickline(scene, scaled_radius)

    def adjust_colors(self, scene):
        """

        :param scene:
        :param tcolor:
        :param pcount:
        :return:
        """
        mono = self.monochrome()
        if mono:
            # We can get away without using a color array.
            rendered_color = Rgb(self.color[0][0], self.color[0][1], self.color[0][2])
            if scene.anaglyph:
                if scene.coloranaglyph:
                    rendered_color.desaturate()#.gl_set(self.opacity)
                else:
                    rendered_color.grayscale()#.gl_set(self.opacity)
            else:
                rendered_color#.gl_set(self.opacity)
        else:
            gl.glEnableClientState(gl.GL_COLOR_ARRAY)
            if scene.anaglyph:
                # Must desaturate or grayscale the color.

                for i in range(0, self.count):
                    rendered_color = Rgb(self.color[i])
                    if scene.coloranaglyph:
                        rendered_color = rendered_color.desaturate()
                    else:
                        rendered_color = rendered_color.grayscale()
                    self.color[i] = rendered_color
        return mono

    def thickline(self, scene, scaled_radius):
        """

        :param scene:
        :param spos:
        :param tcolor:
        :param pcount:
        :param scaled_radius:
        :return:
        """
        cost = self.curve_sc
        sint = cost + self.sides
        lastA = Vector()  # unit vector of previous segment

        if self.count < 2:
            return
        closed = self.pos[0] == self.pos[-1]

        vcount = self.count*2 - closed  # The number of vertices along each edge of the
        # curve
        projected = vcount*self.sides*[Vector()]
        normals = vcount*self.sides*[Vector()]
        light = vcount*self.sides*[Rgb()]

        # pos and color iterators
        if closed:
            i = 0
        else:
            i = self.sides
        mono = self.adjust_colors(scene)

        # eliminate initial duplicate points
        start = self.pos[0]
        reduce = 0
        pos_index = 0
        while pos_index < self.count:
            next = self.pos[pos_index]
            A = (next-start).norm()
            if not A:
                reduce += 1
                del self.pos[pos_index]
                del self.color[pos_index]
                continue
            pos_index += 1
        if self.count < 2:
            return
        pos_index = 0
        for corner in range(0, self.count):
            current = self.pos[pos_index]
            next = Vector()
            A = Vector()
            bisecting_plane_normal = Vector()
            sectheta = None
            if corner != self.count-1:
                next = self.pos[pos_index+1]  # The next vector in pos
                A = (next - current).norm()
                if not A:
                    A = lastA
                bisecting_plane_normal = (A + lastA).norm()
                if not bisecting_plane_normal:  # < Exactly 180 degree bend
                    bisecting_plane_normal = Vector([0, 0, 1]).cross(A)
                    if not bisecting_plane_normal:
                        bisecting_plane_normal = Vector([0, 1, 0]).cross(A)
                sectheta = bisecting_plane_normal.dot(lastA)
                if sectheta:
                    sectheta = 1.0 / sectheta

            if corner == 0:
                y = Vector([0, 1, 0])
                x = A.cross(y).norm()
                if not x:
                    x = A.cross(Vector([0, 0, 1])).norm()
                y = x.cross(A).norm()

                if not x or not y or x == y:
                    raise RuntimeError("Degenerate curve case!")

                # scale radii
                x *= scaled_radius
                y *= scaled_radius

                for a in range(0, self.sides):
                    rel = x*sint[a] + y*cost[a]  # first point is "up"

                    normals[a+i] = rel.norm()
                    projected[a+i] = current + rel
                    if not mono:
                        light[a+i] = self.color[pos_index]

                    if not closed:
                        # Cap start of curve
                        projected[a] = current
                        normals[a] = -A
                        if not mono:
                            light[a] = light[a+i]
                i += self.sides
            else:
                Adot = A.dot(next - current)
                for a in range(0, self.sides):
                    prev_start = projected[i+a-self.sides]
                    rel = current - prev_start
                    t = rel.dot(lastA)
                    if corner != self.count-1 and sectheta > 0.0:
                        t1 = (rel.dot(bisecting_plane_normal)) * sectheta
                        t1 = max(t1, t - Adot)
                        t = max(0.0, min(t, t1))
                    prev_end = prev_start + lastA*t

                    projected[i+a] = prev_end
                    normals[i+a] = normals[i+a-self.sides]
                    if not mono:
                        light[i+a] = self.color[pos_index]

                    if corner != self.count-1:
                        diff_normal = bisecting_plane_normal*2*(prev_end-current).dot(
                            bisecting_plane_normal)
                        next_start = prev_end - diff_normal
                        rel = next_start - current

                        projected[i+a+self.sides] = next_start
                        normals[i+a+self.sides] = (rel - A*A.dot(next_start-current))\
                            .norm()
                        if not mono:
                            light[i+a+self.sides] = light[i+a]
                    elif not closed:
                        # Cap end of curve
                        for a in range(0, self.sides):
                            projected[i+a+self.sides] = current
                            normals[i+a+self.sides] = lastA
                            if not mono:
                                light[i+a+self.sides] = light[a+i]
                i += 2*self.sides
            lastA = A
            pos_index += 1

        if closed:
            # Connect the end of the curve to the start... can be ugly because the basis
            # has gotten twisted around!
            i = (vcount - 1)*self.sides
            for a in range(0, self.sides):
                projected[i+a] = projected[a]
                normals[i+a] = normals[a]
                if not mono:
                    light[i+a] = light[a]

        # Thick lines are often used to represent smooth curves, so we want
        # to smooth the normals at the joints.  But that can make a sharp corner
        # do odd things, so we smoothly disable the smoothing when the joint angle
        # is too big.  This is somewhat arbitrary but seems to work well.
        if closed:
            prev_i = (vcount-1)*self.sides
            i = 0
        else:
            prev_i = 0
            i = self.sides
        '''
        while i < vcount*self.sides:
            for a in range(0, self.sides):
                n1 = normals[i+a]
                n2 = normals[prev_i+a]
                smooth_amount = (n1.dot(n2) - .65) * 4.0
                smooth_amount = min(1.0, max(0.0, smooth_amount))
                if smooth_amount:
                    n_smooth = (n1+n2).norm() * smooth_amount
                    n1 = n1 * (1-smooth_amount) + n_smooth
                    n2 = n2 * (1-smooth_amount) + n_smooth
            prev_i = i + self.sides
            i = 2 * self.sides
        '''
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_NORMAL_ARRAY)
        if not mono:
            gl.glEnableClientState(gl.GL_COLOR_ARRAY)

        ind = 0
        for a in range(0, self.sides):
            ai = a
            if a == self.sides-1:
                ind += 256  # upper portion of curve_slice indices, for the last side
                ai = 0
            # List all the vertices for the ai-th side of the thick line:
            for i in range(0, vcount, 127):

                vertexPointer = make_pointer(i*self.sides + ai, projected)
                print(type(projected), projected)
                gl.glVertexPointer(3, gl.GL_FLOAT, 6, vertexPointer)
                print(type(light), light)
                if not mono:
                    colorPointer = make_pointer((i*self.sides + ai), light)
                    gl.glColorPointer(3, gl.GL_FLOAT, 0, colorPointer)
                normalPointer = make_pointer(i*self.sides + ai, normals)
                gl.glNormalPointer(gl.GL_FLOAT, 0, normalPointer)

                if vcount-i < 128:
                    pointer = make_pointer(ind, self.curve_slice, c_int)
                    gl.glDrawElements(gl.GL_TRIANGLE_STRIP, 2*(vcount-i),
                                          gl.GL_UNSIGNED_INT, pointer)

                else:
                    gl.glDrawElements(gl.GL_TRIANGLE_STRIP, 256, gl.GL_UNSIGNED_INT,
                                      make_pointer(ind, self.curve_slice, c_int))

        if not mono:
            gl.glDisableClientState(gl.GL_COLOR_ARRAY)