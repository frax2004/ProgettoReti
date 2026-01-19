import raylib as rl
import math
from dataclasses import dataclass
import json

font = None
ALGORITHM = 'astar'

@dataclass
class Vector2:
  x: float
  y: float

  def unwrap(self):
    return (self.x, self.y)

@dataclass
class Color:
  r: int
  g: int
  b: int
  a: int

  def unwrap(self):
    return (self.r, self.g, self.b, self.a)

@dataclass
class Rectangle:
  x: float
  y: float
  width: float
  height: float

  def unwrap(self):
    return (self.x, self.y, self.width, self.height)

Vec2 = Vector2
Color = Color
Rect = Rectangle
Node = int
Edge = tuple[Node, Node]

def vec2(x: float, y: float) -> Vec2:
  v = Vec2(0, 0)
  v.x, v.y = x, y
  return v

def color(r, g, b, a = 255) -> Color:
  c = Color(0, 0, 0, 255)
  c.r, c.g, c.b, c.a = r, g, b, a
  return c

def rect(pos: Vec2, size: Vec2) -> Rect:
  r = Rect(0, 0, 0, 0)
  r.x, r.y, r.width, r.height = pos.x, pos.y, size.x, size.y
  return r

class Graph:
  def __init__(self, nodes: dict[Node, Vec2], edges: set[Edge], weights: dict[Edge, float] = None):
    self.nodes = nodes
    self.edges = edges
    self.weights = weights if weights else { edge : 1.0 for edge in self.edges }

def show(size: tuple, title: str, update, draw):
  global font
  rl.InitWindow(size[0], size[1], title.encode())
  rl.SetTargetFPS(60)
  rl.SetWindowState(rl.FLAG_WINDOW_HIGHDPI | rl.FLAG_WINDOW_RESIZABLE)

  font = rl.LoadFont(b"/usr/share/fonts/truetype/msttcorefonts/ariblk.ttf")

  while not rl.WindowShouldClose():
    update()
    rl.BeginDrawing()
    rl.ClearBackground(rl.BLACK)
    draw()
    rl.EndDrawing()
  
  rl.UnloadFont(font)
  rl.CloseWindow()


def update(): 
  if rl.IsKeyPressed(rl.KEY_S) and rl.IsKeyDown(rl.KEY_LEFT_CONTROL):
    rl.TakeScreenshot(f'{ALGORITHM}_graphs_plots.png'.encode())

def draw_graph(graph: Graph, rec: Rect):
  topo_size = vec2(16, 10)
  
  col = color(150, 150, 150)
  size = vec2(rec.width, rec.height)

  def world2rec(pos: Vec2):
    return vec2(
      (pos.x / topo_size.x)*size.x, 
      (pos.y / topo_size.y)*size.y
    )

  max_weight = max(graph.weights.values()) if graph.weights else 1
  for edge in graph.edges:
    src, dst = world2rec(graph.nodes[edge[0]]), world2rec(graph.nodes[edge[1]])
    weight = graph.weights.get(edge, 1.0)

    rl.DrawLineEx(
      vec2(rec.x + src.x, rec.y + src.y).unwrap(),
      vec2(rec.x + dst.x, rec.y + dst.y).unwrap(),
      2.0,
      rl.ColorLerp(rl.BLUE, rl.RED, 1 - weight/max_weight)
    )

  for _, pos in graph.nodes.items():
    pos = world2rec(pos)
    rl.DrawCircleV(
      vec2(rec.x + pos.x, rec.y + pos.y).unwrap(),
      2,
      col.unwrap()
    )

  if graph.last_path is not None:
    for source, dest in [(graph.last_path[i], graph.last_path[i+1]) for i in range(len(graph.last_path)-1)]:
      src, dst = world2rec(graph.nodes[source]), world2rec(graph.nodes[dest])
      rl.DrawLineEx(
        vec2(rec.x + src.x, rec.y + src.y).unwrap(),
        vec2(rec.x + dst.x, rec.y + dst.y).unwrap(),
        3.5,
        rl.YELLOW
      )

def draw_graphs(graphs: list[Graph]):
  WIDTH, HEIGHT = rl.GetRenderWidth(), rl.GetRenderHeight()
  l = math.ceil(math.sqrt(len(graphs)))
  size = vec2(WIDTH/l, HEIGHT/l)

  for i, graph in enumerate(graphs):
    rec = rect(
      vec2(size.x * (i%l), size.y * (i//l)),
      size
    )

    rl.DrawRectangleLinesEx(rec.unwrap(), 2.0, rl.GREEN)
    rl.DrawTextEx(
      font,
      f"t = {graph.timestamp}".encode(),
      vec2(rec.x + 4, rec.y + 2).unwrap(),
      20,
      1.0,
      rl.WHITE
    )

    draw_graph(graph, rec)

def load_graphs() -> list[Graph]:
  graphs: list[Graph] = []

  frames: list[dict] = []
  with open(f'{ALGORITHM}_weighted_paths.json') as file:
    frames = json.load(file)

  for frame in frames:
    graph = Graph(
      nodes = {
        # ----- hosts -----
        1: vec2(4, 2),   #h1
        2: vec2(2, 2),   #h2
        3: vec2(2, 8),   #h3
        4: vec2(14, 4),  #h4
        5: vec2(14, 8),  #h5

        # ----- switches -----
        6: vec2(6, 4),   #sw1
        7: vec2(8, 4),   #sw2
        8: vec2(10, 4),  #sw3
        9: vec2(6, 6),   #sw4
        10: vec2(8, 6),  #sw5
        11: vec2(10, 6), #sw6
        12: vec2(6, 8),  #sw7
        13: vec2(8, 8),  #sw8
        14: vec2(10, 8)  #sw9
      },
      edges = {
        # ----- host-switch -----
        (1, 6), (2, 6), (3, 12), (4, 8), (5, 14),
        # ----- switch-switch -----
        (6, 7), (7, 8), (9, 10), (10, 11), (12, 13), (13, 14), # horizontal
        (6, 9), (9, 12), (7, 10), (10, 13), (8, 11), (11, 14) # vertical
      }
    )

    for weighted_edge in frame.get("weights"):
      source = weighted_edge.get('source')
      dest = weighted_edge.get('dest')
      weight = weighted_edge.get('weight')

      graph.weights[(source, dest)] = weight
      graph.weights[(dest, source)] = weight

    graph.last_path = frame.get('last_path')
    graph.timestamp = frame.get('timestamp')
    graphs.append(graph)
  
  return graphs


def plot_graphs():
  graphs = load_graphs()
  show((1200, 800), 'graphs', update, lambda: draw_graphs(graphs))

if __name__ == '__main__':
  plot_graphs()

