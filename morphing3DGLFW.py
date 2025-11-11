# morphing3DGLFW.py
# [mvfm] - Implementação do Morpher3D usando GLFW
#
# Criado : 11/11/2025  ||  Última vez Alterado : 11/11/2025
#
# Teclas:
#    m - pausar/retomar morphing
#    n - mostrar/ocultar normais
#    w/q - subir/descer câmera
#    setas - afastar/aproximar, inclinar visão
#    s - avançar um passo de morph (quando pausado)
#    ESC - sair

from OpenGL.GL import *
from OpenGL.GLU import *
import glfw
import sys
import numpy as np
import math

# Config e estados globais
windowWidth, windowHeight = 1024, 700
rotation = 0.0

modelA = None
modelB = None
associations = []

morph_t = 0.0
morph_dir = 1
animar = True
mostrarNormais = False

cameraPos = [0.0, 0.0, 3.5]
altVisao = 0.0



# Utilitários OBJ (mesmos da versão Windows)
def carregar_obj(path):
    verts, faces, normals = [], [], []
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('v '):
                parts = line.strip().split()
                x, y, z = map(float, parts[1:4])
                verts.append(np.array((x, y, z), dtype=float))
            elif line.startswith('vn '):
                parts = line.strip().split()
                x, y, z = map(float, parts[1:4])
                normals.append(np.array((x, y, z), dtype=float))
            elif line.startswith('f '):
                parts = line.strip().split()[1:]
                idxs = []
                for p in parts:
                    if '/' in p:
                        v_idx = p.split('/')[0]
                    else:
                        v_idx = p
                    if v_idx == '':
                        continue
                    idxs.append(int(v_idx) - 1)
                if len(idxs) == 3:
                    faces.append(idxs)
                elif len(idxs) > 3:
                    for i in range(1, len(idxs) - 1):
                        faces.append([idxs[0], idxs[i], idxs[i + 1]])
    return {'vertices': verts, 'faces': faces, 'normals': normals}


def normalizar_modelo(model):
    v = np.array(model['vertices'])
    if v.size == 0:
        return
    centro = np.mean(v, axis=0)
    v -= centro
    max_dist = np.max(np.linalg.norm(v, axis=1))
    if max_dist == 0:
        max_dist = 1.0
    v /= max_dist
    model['vertices'] = [np.array(row) for row in v]


def centroid_of_face(face, vertices):
    pts = np.array([vertices[i] for i in face])
    return np.mean(pts, axis=0)


def face_normal(face, vertices):
    a = np.array(vertices[face[0]])
    b = np.array(vertices[face[1]])
    c = np.array(vertices[face[2]])
    u = b - a
    v = c - a
    n = np.cross(u, v)
    norm = np.linalg.norm(n)
    return n / norm if norm != 0 else np.array((0.0, 0.0, 1.0))


def associate_faces(modelA, modelB):
    centA = [centroid_of_face(f, modelA['vertices']) for f in modelA['faces']]
    centB = [centroid_of_face(f, modelB['vertices']) for f in modelB['faces']]
    assoc = []
    for c in centA:
        dists = [np.linalg.norm(c - cb) for cb in centB]
        assoc.append(int(np.argmin(dists)) if dists else None)
    return assoc


def align_triangle_vertices(vertsA, vertsB):
    if len(vertsA) != 3 or len(vertsB) != 3:
        vb = [np.array(v) for v in vertsB]
        while len(vb) < 3:
            vb.append(vb[-1])
        return vb[:3]
    vb = [np.array(v) for v in vertsB]
    va = [np.array(v) for v in vertsA]
    best = vb
    best_cost = float('inf')
    permutations = [
        vb,
        [vb[1], vb[2], vb[0]],
        [vb[2], vb[0], vb[1]],
        [vb[2], vb[1], vb[0]],
        [vb[1], vb[0], vb[2]],
        [vb[0], vb[2], vb[1]]
    ]
    for perm in permutations:
        cost = sum(np.linalg.norm(va[i] - perm[i]) for i in range(3))
        if cost < best_cost:
            best_cost = cost
            best = perm
    return best


# Desenho principal
def desenhar_morph(t):
    global modelA, modelB, associations
    glBegin(GL_TRIANGLES)
    for i, faceA in enumerate(modelA['faces']):
        j = associations[i] if i < len(associations) else None
        if j is None or j >= len(modelB['faces']):
            verts = [modelA['vertices'][idx] for idx in faceA]
            n = face_normal(faceA, modelA['vertices'])
            glNormal3fv(n)
            for v in verts:
                glVertex3fv(v)
            continue
        faceB = modelB['faces'][j]
        vertsA = [modelA['vertices'][idx] for idx in faceA]
        vertsB = [modelB['vertices'][idx] for idx in faceB]
        vertsB_aligned = align_triangle_vertices(vertsA, vertsB)
        tri = [(1 - t) * np.array(vertsA[k]) + t * np.array(vertsB_aligned[k]) for k in range(3)]
        n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
        n_norm = np.linalg.norm(n)
        if n_norm != 0:
            n = n / n_norm
        else:
            n = np.array((0.0, 0.0, 1.0))
        glNormal3fv(n)
        for v in tri:
            glVertex3fv(v)
    glEnd()


# Inicialização
def inicializar():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_NORMALIZE)
    glShadeModel(GL_SMOOTH)
    glClearColor(0.06, 0.06, 0.06, 1.0)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.95, 0.95, 0.95, 1.0])
    glLightfv(GL_LIGHT0, GL_AMBIENT, [0.25, 0.25, 0.25, 1.0])
    glLightfv(GL_LIGHT0, GL_SPECULAR, [0.8, 0.8, 0.8, 1.0])
    glLightfv(GL_LIGHT0, GL_POSITION, [5.0, 10.0, 5.0, 1.0])
    glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
    glMaterialfv(GL_FRONT_AND_BACK, GL_SHININESS, [32.0])


# GLFW Callbacks
def on_key(window, key, scancode, action, mods):
    global cameraPos, mostrarNormais, animar, morph_t
    if action not in [glfw.PRESS, glfw.REPEAT]:
        return
    if key == glfw.KEY_ESCAPE:
        glfw.set_window_should_close(window, True)
    elif key == glfw.KEY_Q:
        cameraPos[1] += 0.2
    elif key == glfw.KEY_E:
        cameraPos[1] -= 0.2
    elif key == glfw.KEY_W:
        cameraPos[2] -= 0.2
    elif key == glfw.KEY_S:
        if not animar:
            morph_t = min(1.0, morph_t + 0.02)
    elif key == glfw.KEY_M:
        animar = not animar
    elif key == glfw.KEY_N:
        mostrarNormais = not mostrarNormais


def on_resize(window, w, h):
    global windowWidth, windowHeight
    h = max(h, 1)
    windowWidth, windowHeight = w, h
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, w / float(h), 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)

# Loop principal
def main():
    global modelA, modelB, associations, rotation, morph_t, morph_dir

    if len(sys.argv) < 3:
        print("Uso: python morphing3D_glfw.py modeloA.obj modeloB.obj")
        sys.exit(1)

    pathA, pathB = sys.argv[1], sys.argv[2]
    modelA = carregar_obj(pathA)
    modelB = carregar_obj(pathB)

    normalizar_modelo(modelA)
    normalizar_modelo(modelB)
    associations = associate_faces(modelA, modelB)

    if not glfw.init():
        print("Erro: falha ao inicializar GLFW.")
        sys.exit(1)

    window = glfw.create_window(windowWidth, windowHeight, "morphing3D - [mvfm]", None, None)
    if not window:
        glfw.terminate()
        print("Erro ao criar janela GLFW.")
        sys.exit(1)

    glfw.make_context_current(window)
    glfw.set_key_callback(window, on_key)
    glfw.set_window_size_callback(window, on_resize)

    inicializar()

    print("Modelos carregados e normalizados:")
    print(f"  A: {len(modelA['vertices'])} vértices, {len(modelA['faces'])} faces")
    print(f"  B: {len(modelB['vertices'])} vértices, {len(modelB['faces'])} faces")

    while not glfw.window_should_close(window):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        gluLookAt(cameraPos[0], cameraPos[1], cameraPos[2], 0, altVisao, 0, 0, 1, 0)

        glLightfv(GL_LIGHT0, GL_POSITION, [0.0, 5.0, 5.0, 1.0])
        glPushMatrix()
        glRotatef(rotation, 0, 1, 0)
        desenhar_morph(morph_t)
        glPopMatrix()

        glfw.swap_buffers(window)
        glfw.poll_events()

        if animar:
            morph_t += 0.006 * morph_dir
            if morph_t >= 1.0:
                morph_t = 1.0
                morph_dir = -1
            elif morph_t <= 0.0:
                morph_t = 0.0
                morph_dir = 1

        rotation = (rotation + 0.15) % 360

    glfw.terminate()


if __name__ == "__main__":
    main()
