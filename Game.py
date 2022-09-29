import pygame
import pygame.gfxdraw
import time
import math
import random
import sys
from typing import Any
from DataStructs import LinkedCircle
from abc import ABC, abstractmethod

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
pygame.init()
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 32, pygame.font.Font.bold)
pygame.display.set_icon(pygame.image.load("Assets/Icon.png"))
pygame.display.set_caption("Complex Conflict")
display = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
screen = pygame.Surface((1920, 1080)).convert_alpha()


def draw_on(surface: pygame.Surface, *strings: str):
    for i, string in enumerate(strings):
        surface.blit(font.render(string, True, (255, 255, 255)), (100, 150 + (i * 50)))


def dir_to(
        mp: tuple[float | int, float | int] | pygame.math.Vector2,
        tp: tuple[float | int, float | int] | pygame.math.Vector2
) -> float:
    rads = math.atan2(-(tp[1] - mp[1]), tp[0] - mp[0])
    rads %= 2 * math.pi
    return math.degrees(rads)


def relative_mouse(m: pygame.Vector2 = None) -> tuple[float, float]:
    if m is None:
        m = pygame.Vector2(pygame.mouse.get_pos())
    x = m.x / (display.get_width() / screen.get_width())
    y = m.y / (display.get_width() * screen.get_height() / screen.get_width() / screen.get_height())
    return x, y


def round_to_360(x: int | float) -> float:
    return math.degrees(math.asin(math.sin(math.radians(x))))


def dis_to(mp: tuple[float, float] | pygame.Vector2, tp: tuple[float, float] | pygame.Vector2) -> float:
    return math.hypot(mp[0] - tp[0], mp[1] - tp[1])


def face_to(self: pygame.sprite.Sprite,
            ang: tuple[float, float] | pygame.Vector2,
            turn_limit: int | float,
            f: callable = None) -> None:
    angle = dir_to(self.rect.center, ang)
    turn = math.sin(math.radians(angle - self.angle)) * turn_limit
    self.angle += turn
    if f:
        f(turn)


def move(self, amount: int | float) -> None:
    self.v = pygame.math.Vector2((amount, 0)).rotate(self.angle)
    self.pos.x += self.v.x
    self.pos.y -= self.v.y


def stay_inside_view(self) -> None:
    def set_pos():
        if hasattr(self, "pos"):
            self.pos = self.rect.center

    if self.rect.left < 0:
        self.rect.left = 0
        set_pos()
    if self.rect.right > screen.get_width():
        self.rect.right = screen.get_width()
        set_pos()
    if self.rect.top < 0:
        self.rect.top = 0
        set_pos()
    if self.rect.bottom > screen.get_height():
        self.rect.bottom = screen.get_height()
        set_pos()


def gimbal_limit(self, angle: int | float, limit: int | float) -> bool:
    """
    Return a bool if the target of the missile is outside its turn radius.
    param self: an object that has an angle attribute.
    param angle: an angle as an integer or float to where the missile is meant to fly.
    param limit: the max. difference in degrees between where the missile is pointed and where it is meant to fly.
    return: bool if the gimbal limit was reached.
    """
    return abs(((self.angle - angle) + 180) % 360 - 180) > limit


def closest_target(self, sprites: list, max_range: int | float = 250, angle_limit: int | float = 0, exclude=None):
    compare = {max_range: None}
    for sprite in sprites:
        if sprite is not exclude:
            if angle_limit == 0:
                compare[dis_to(self.rect.center, sprite.rect.center)] = sprite
            else:
                if not gimbal_limit(self, dir_to(self.rect.center, sprite.rect.center), angle_limit):
                    compare[dis_to(self.rect.center, sprite.rect.center)] = sprite

    m = min(compare.keys())
    return compare[m]


def all_overlaps(self, group: pygame.sprite.Group, exclude=None) -> list:
    """
    The listed passed into the filter call checks rect collisions, then, only the objects
    that are also mask colliding will be keep, the final result will be returned
    """
    r_list = list(filter(lambda obj: self.mask.overlap(obj.mask,
                                                       (obj.rect.x - self.rect.x, obj.rect.y - self.rect.y)),
                         pygame.sprite.spritecollide(self, group, False)))
    if exclude is not None and exclude in r_list:
        r_list.remove(exclude)
    return r_list


def first_overlap(caller: pygame.sprite.Sprite,
                  *sprites: pygame.sprite.Sprite) -> pygame.sprite.Sprite | None | Any:
    for sprite in sprites:
        if overlapping(caller, sprite):
            return sprite
    return None


def overlapping(caller: pygame.sprite.Sprite, *sprites: pygame.sprite.Sprite) -> bool:
    for sprite in sprites:
        if caller.mask.overlap(sprite.mask, (sprite.rect.x - caller.rect.x, sprite.rect.y - caller.rect.y)):
            return True
    return False


def point_colliding(point: tuple[int, int], *sprites: pygame.sprite.Sprite | Any) -> tuple[Any | pygame.sprite.Sprite]:
    return tuple(filter(lambda sprite: sprite.rect.collidepoint(point), sprites))


def max_reach(start_point: tuple[int, int] | pygame.Vector2,
              end_point: tuple[int, int] | pygame.Vector2,
              m_range: int | float) -> tuple[float, float]:
    to_dir = dir_to(start_point, end_point)
    to_len = min(m_range, dis_to(start_point, end_point))
    return (math.cos(math.radians(to_dir)) * to_len) + start_point[0], \
           (-math.sin(math.radians(to_dir)) * to_len) + start_point[1]


def predicted_los(self, target, speed, r=0) -> tuple:
    target: Player | SAM | Harm | Path_Guided_Missile
    if target:
        t = int(dis_to(self.rect.center,
                       predicted_los(self, target, speed, r=r + 1) if r <= 2 else target.rect.center) / speed)
        return target.rect.centerx + (target.v.x * t), target.rect.centery + (
                -target.v.y * t)
    else:
        raise ValueError("No target given")


def check_out_of_bounds(self):
    if self.rect.right < 0 or self.rect.left > screen.get_width() or \
            self.rect.bottom < 0 or self.rect.top > screen.get_height():
        self.kill()


def fill(surface, color):
    w, h = surface.get_size()
    r, g, b, _ = color
    for x in range(w):
        for y in range(h):
            a = surface.get_at((x, y))[3]
            surface.set_at((x, y), pygame.Color(r, g, b, a))


class GUI(pygame.sprite.Sprite):
    @classmethod
    def find_gui(cls, guis, gui_id: str):
        for gui in guis:
            if gui.gui_id == gui_id:
                return gui
        return None

    class GUI_Button(pygame.sprite.Sprite):
        def __init__(self, gui, relative_pos, filepath: str, on_click: callable = None, on_click_args: list = None):
            pygame.sprite.Sprite.__init__(self)
            self.gui = gui
            self.relative_pos = relative_pos
            self.callback = on_click
            self.callback_args = on_click_args
            self.sub_gui = None
            self.cache = None
            self.image = pygame.transform.scale(pygame.image.load(f"Assets/GUI_Buttons/{filepath}").convert_alpha(),
                                                self.gui.box_size)
            self.image.set_alpha(191)
            self.rect = self.image.get_rect(topleft=pygame.math.Vector2(gui.rect.topleft) + relative_pos)

            gui_group.add(self)

        def update(self) -> None:
            if self.sub_gui is not None and self.sub_gui.done:
                self.callback_f()
            self.rect.topleft = pygame.math.Vector2(self.gui.rect.topleft) + self.relative_pos
            if pygame.mouse.get_pressed()[0] and self.rect.collidepoint(relative_mouse()):
                self.callback_f()

        def callback_f(self):
            self.callback(self, *self.callback_args)

        def destroy(self):
            if self.sub_gui is not None:
                self.sub_gui.destroy()
            self.kill()

    class GUI_Selector(pygame.sprite.Sprite):
        def __init__(self, gui):
            super().__init__()
            self.gui = gui
            self.image = pygame.Surface(gui.box_size)
            self.image.fill("Green")
            self.image.set_alpha(160)
            self.rect = self.image.get_rect(topleft=pygame.math.Vector2(gui.rect.topleft))

            gui_group.add(self)

        def update(self) -> None:
            self.rect.topleft = pygame.math.Vector2(self.gui.buttons.cur.data.rect.topleft)

    def __init__(self, gui_id: str, size: tuple[int, int], content: list[tuple[str, callable, list | tuple]] = None,
                 box_size: tuple[int, int] = (60, 60), output_len: int = None, parent=None,
                 callback: callable = None, callback_args=None, **pos):
        super().__init__()
        if callback_args is None:
            callback_args = []
        self.output = []
        self.output_len = output_len
        self.done = False
        self.gui_id = gui_id
        self.pos_args = pos
        self.parent = parent
        self.callback = callback
        self.callback_args = callback_args
        self.workspace = {}
        self.box_size = pygame.math.Vector2(box_size)
        self.image = pygame.Surface((self.box_size[0] * size[0], self.box_size[1] * size[1]))
        self.image.fill("green")
        self.image.set_alpha(0)
        self.rect = self.image.get_rect(**self.pos_args)
        self.content = LinkedCircle(*content)
        self.buttons = LinkedCircle()

        counter = 0
        cur = self.content.head
        while True:
            x = counter % size[0]
            y = counter // size[0]
            button = self.GUI_Button(self, (x * self.box_size.x, y * self.box_size.y), filepath=cur.data[0],
                                     on_click=cur.data[1], on_click_args=cur.data[2])
            self.buttons.add(button)

            cur = cur.next_node
            counter += 1
            if counter >= size[0] * size[1]:
                break

        self.selector = self.GUI_Selector(self)
        gui_group.add(self)

    def destroy(self, done=False):
        cur = self.buttons.head
        while True:
            cur.data.destroy()
            cur = cur.next_node
            if cur == self.buttons.head:
                break
        self.done = done
        self.selector.kill()
        if isinstance(self.parent, Ground_Controller):
            self.parent.guis.remove(self)
        if isinstance(self.parent, self.GUI_Button):
            self.parent.sub_gui = None
        self.kill()

    def set_rect(self, **kwargs):
        self.pos_args = kwargs

    def update(self) -> None:
        if isinstance(self.output_len, int) and len(self.output) >= self.output_len:
            self.done = True
        if self.callback is not None:
            self.callback(self, *self.callback_args)
        self.rect = self.image.get_rect(**self.pos_args)
        if self.rect.right > screen.get_width():
            self.rect.right = screen.get_width()
        elif self.rect.left < 0:
            self.rect.left = 0
        if self.rect.bottom > screen.get_height():
            self.rect.bottom = screen.get_height()
        elif self.rect.top < 0:
            self.rect.top = 0


class UI:
    class Button(pygame.sprite.Sprite):
        def __init__(self, icon: str, button_callable: callable, *groups, args=(), size=(200, 100), **kwargs):
            super().__init__()
            load = pygame.image.load(f"Assets/Menu_Buttons/{icon}.png").convert_alpha()
            self.image = pygame.transform.scale(load, size)
            self.rect = self.image.get_rect(**kwargs)

            self.callable = button_callable
            self.args = args

            for group in groups:
                group.add(self)

        def call(self):
            self.callable(*self.args)

    class Display(pygame.sprite.Sprite):
        def __init__(self, *groups, size=1.0, **kwargs):
            super().__init__()
            self.stored = pygame.transform.rotozoom(pygame.image.load(f"Assets/Menu_Buttons/emtpy.png").convert_alpha(),
                                                    0, size)
            self.image = self.stored.copy()
            self.rect = self.image.get_rect(**kwargs)

            for group in groups:
                group.add(self)

        def display_value(self, value, font_size=50):
            base = self.stored.copy()
            base_rect = base.get_rect()
            text = pygame.font.SysFont("arial", font_size, pygame.font.Font.bold).render(f"{value}", True,
                                                                                         (255, 255, 255))
            text_rect = text.get_rect(center=base_rect.center)
            base.blit(text, text_rect)
            self.image = base.copy()

    class Label(pygame.sprite.Sprite):
        def __init__(self, text: str, font_size: int, *groups, text_font="arial", color=(255, 255, 255), **kwargs):
            super().__init__()
            f = pygame.font.SysFont(text_font, font_size, pygame.font.Font.bold)
            f.underline = True
            self.image = f.render(f"{text}", True, color)
            self.rect = self.image.get_rect(**kwargs)

            for group in groups:
                group.add(self)

    class Loading_Box(pygame.sprite.Sprite):
        def __init__(self, uis: pygame.sprite.Group, size: tuple[int, int], **kwargs):
            super().__init__()
            self.stored = pygame.Surface(size, pygame.SRCALPHA)
            self.image = self.stored.copy()
            self.rect = self.image.get_rect(**kwargs)

            uis.add(self)

        def display_decimal(self, decimal) -> None:
            base = self.stored.copy()
            base_rect = base.get_rect()
            # base, "blue", base_rect, 0, decimal * (2 * math.pi), int(base.get_width() / 2)
            pygame.draw.arc(base, (0, 0, 255), base_rect, 0, decimal * (2 * math.pi), int(base.get_width() / 2))
            self.image = base.copy()

    class Ratio_Bar(pygame.sprite.Sprite):
        def __init__(self, uis: pygame.sprite.Group, size: tuple[int, int], border: int, **kwargs):
            super().__init__()
            self.stored = pygame.Surface(size)
            self.stored.fill((65, 66, 65))
            self.border = border
            self.image = self.stored.copy()
            self.rect = self.image.get_rect(**kwargs)

            uis.add(self)

        def display_ratio(self, ratio: float, color_l: tuple | str = "Blue", color_r: tuple | str = "Red"):
            base = self.stored.copy()
            base_rect = base.get_rect()
            left_rect = pygame.Rect(base_rect.left + self.border, base_rect.top + self.border,
                                    (base_rect.right - (self.border * 2)) * ratio, base_rect.height - (self.border * 2))
            right_rect = pygame.Rect(left_rect.right, left_rect.top,
                                     (base_rect.right - (self.border * 2)) - left_rect.width, left_rect.height)
            pygame.draw.rect(base, color_l, left_rect)
            pygame.draw.rect(base, color_r, right_rect)
            self.image = base.copy()


class Pointer(pygame.sprite.Sprite):
    def __init__(self, main_id, group, **kwargs):
        super(Pointer, self).__init__()
        self.joystick = Xbox_Controller(main_id=main_id)
        self.image = pygame.transform.rotozoom(pygame.image.load("Assets/pointer.png").convert_alpha(), 0, 0.05)
        self.rect = self.image.get_rect(**kwargs)
        self.mask = pygame.mask.from_surface(self.image)
        group.add(self)

    def update(self, *args: Any, **kwargs: Any) -> None:
        if self.joystick.joystick.get_instance_id() not in kwargs.get("joystick"):
            self.kill()
            return None
        self.joystick.clear_cache()
        self.move(pygame.math.Vector2(self.joystick.stick(0, 1)) * 7.5, relative=True)
        if self.joystick.button_check(0):
            for button in kwargs.get("button", ()):
                if button.rect.collidepoint(self.rect.midtop):
                    button.call()
        stay_inside_view(self)

    def move(self, xy: pygame.math.Vector2 | tuple[int | float, int | float], relative=False):
        if relative:
            self.rect.center = pygame.math.Vector2(xy) + self.rect.center
        else:
            self.rect.center = pygame.math.Vector2(xy)


class Ground(pygame.sprite.Sprite, ABC):
    @abstractmethod
    def __init__(self, team, image_path: str, image_size=1.0, **pos_args):
        super().__init__()
        self.team = team
        self.image = pygame.transform.rotozoom(pygame.image.load(image_path), 0, image_size).convert_alpha()
        self.rect = self.image.get_rect(**pos_args)
        self.mask = pygame.mask.from_surface(self.image)
        self.stationed_vehicles = pygame.sprite.Group()
        self.blueprints = pygame.sprite.Group()

    def spawn_bunker(self, *bunkers: tuple[int, int] | pygame.Vector2):
        self.team: Team
        for bunker in bunkers:
            bunker_bp = Blueprint(self.team.controller, Bunker, delay=Bunker.delay)
            bunker_bp.rect.center = pygame.Vector2(bunker) + self.rect.topleft
            bunker_bp.place(self)


class Main_Island(Ground):
    def __init__(self, team, ground_group):
        pos_args = {"topleft": (0, 0)} if team.team_num == 0 else {"topright": (screen.get_width(), 0)}
        super().__init__(team, "Assets/Ground/Island.png", **pos_args)

        self.spawn_bunker((100, 100), (100, 980))

        ground_group.add(self)


class Small_Island(Ground):
    def __init__(self, team, pos, ground_group):
        super(Small_Island, self).__init__(team, "Assets/Ground/small_island.png", image_size=0.4, center=pos)
        self.timer = 0

        self.bunkers = ((self.rect.width / 2, self.rect.height / 2),)
        self.spawn_bunker(*self.bunkers)

        ground_group.add(self)

    def change_team(self):
        self.team: Team
        self.team.captured_land.remove(self)
        self.team = self.team.enemy_team
        self.team.captured_land.add(self)

    def update(self):
        if len(self.stationed_vehicles) + len(self.blueprints) <= 0:
            self.change_team()
            self.spawn_bunker(*self.bunkers)


class Runway(Ground):
    def __init__(self, team, ground_group):
        pos_args = {"midleft": (50, screen.get_height() / 2)} if team.team_num == 0 else {
            "midright": (screen.get_width() - 50, screen.get_height() / 2)}
        super().__init__(team, "Assets/Ground/Runway.png", **pos_args)

        ground_group.add(self)


class PlayerController(ABC):
    def __init__(self, joystick_id, team):
        self.joystick = Xbox_Controller(joystick_id, ) if joystick_id is not None else None
        self.team = team
        self.guis = []

    @abstractmethod
    def handle_keys(self, **kwargs):
        pass


class Xbox_Controller:
    def __init__(self, main_id: int):
        self.connection: bool = True
        self.joystick = pygame.joystick.Joystick(main_id)
        self.joystick.init()
        self.cache = {}
        self.buttons = dict((i, False) for i in range(self.joystick.get_numbuttons()))
        self.hats = {(1, 0): False, (0, 1): False, (-1, 0): False, (0, -1): False}
        self.axes = dict((i, False) for i in range(self.joystick.get_numaxes()))

    def clear_cache(self):
        self.cache.clear()

    def check_dpad(self, x: int, y: int) -> bool:
        if not self.hats.get((x, y)):
            if self.joystick.get_hat(0) == (x, y):
                self.hats[(x, y)] = True
                self.cache[(x, y)] = True
                return True
        else:
            if self.joystick.get_hat(0) == (x, y):
                return False
            else:
                self.hats[(x, y)] = False

    def button_check(self, button: int) -> bool:
        if not self.buttons.get(button):
            if self.joystick.get_button(button):
                self.buttons[button] = True
                self.cache[button] = True
                return True
        else:
            if self.joystick.get_button(button):
                return False
            else:
                self.buttons[button] = False

    def trigger_pressed(self, axis: int, threshold=0.5) -> bool:
        if not self.axes.get(axis):
            if self.joystick.get_axis(axis) > threshold:
                self.axes[axis] = True
                return True
        else:
            if self.joystick.get_axis(axis) > threshold:
                return False
            else:
                self.axes[axis] = False

    def stick(self, axis_x: int, axis_y: int, dead_zone=0.2) -> tuple[float, float]:
        if abs(self.joystick.get_axis(axis_x)) < dead_zone:
            x = 0
        else:
            x = self.joystick.get_axis(axis_x)
        if abs(self.joystick.get_axis(axis_y)) < dead_zone:
            y = 0
        else:
            y = self.joystick.get_axis(axis_y)
        return x, y


class Ground_Controller(PlayerController):
    class Pointer(pygame.sprite.Sprite):
        def __init__(self, controller):
            super().__init__()
            self.controller = controller
            self.pos = pygame.math.Vector2((screen.get_width() / 2, screen.get_height() / 2))
            self.image = pygame.transform.rotozoom(pygame.image.load("Assets/AimCross.png").convert_alpha(), 0, 0.5)
            self.rect = self.image.get_rect(center=self.pos)

            non_traceables.add(self)

        def move(self, xy: pygame.math.Vector2 | tuple[int | float, int | float], relative=False):
            if relative:
                self.pos += pygame.math.Vector2(xy)
            else:
                self.pos = pygame.math.Vector2(xy)
            self.rect.center = self.pos

        def update(self, *args: any, **kwargs: any) -> None:
            stay_inside_view(self)

    def __init__(self, joystick_id, team):
        super().__init__(joystick_id, team)
        self.pointer = self.Pointer(self)
        self.selected_vehicles = pygame.sprite.Group()
        self.click = False
        self.lifespan = 0
        self.in_hand = None

    def create_gui(self):
        def stick_to_pointer(gui: GUI):
            gui.set_rect(topleft=self.pointer.rect.center)

        def close_gui(button: GUI.GUI_Button):
            button.gui.destroy(done=True)
            if isinstance(button.gui.parent, GUI.GUI_Button):
                button.gui.parent.gui.destroy(done=True)
            if button.gui in self.guis:
                self.guis.remove(button.gui)

        def stick_to_parent(gui: GUI):
            gui.set_rect(midtop=gui.parent.gui.rect.midbottom)

        def button_callable(button: GUI.GUI_Button, *args):
            obj = args[0]
            if obj is not None:
                if self.in_hand is not None:
                    self.in_hand.kill()
                delay = obj.delay
                self.in_hand = Blueprint(self, args[0], delay=delay)
                self.in_hand.rect.center = self.pointer.rect.center
                button.gui.parent.gui.destroy(done=True)
            else:
                if self.in_hand is not None:
                    self.in_hand.kill()
                    self.in_hand = None
            button.gui.destroy(done=True)
            self.guis.remove(button.gui)

        def add_vehicles(button: GUI.GUI_Button):
            if button.sub_gui is None:
                button.sub_gui = GUI("vehicles", (11, 1), box_size=(50, 50), content=[
                    ("man_aa.png", button_callable, (ManAA,)),
                    ("vads.png", button_callable, (Vads,)),
                    ("s300.png", button_callable, (Long_Range_SAM,)),
                    ("sa15.png", button_callable, (Medium_Range_SAM,)),
                    ("cwis.png", button_callable, (CWIS,)),
                    ("grad.png", button_callable, (Grad,)),
                    ("cruise.png", button_callable, (Cruise_Missile_Launcher,)),
                    ("jtac.png", button_callable, (JTAC,)),
                    ("rad.png", button_callable, (Search_Radar,)),
                    ("Mid_Radar.png", button_callable, (Medium_Track_Radar,)),
                    ("none.png", button_callable, (None,))
                ], output_len=1, parent=button, callback=stick_to_parent, midtop=button.gui.rect.midbottom)
                self.guis.append(button.sub_gui)

        def add_buildings(button: GUI.GUI_Button):
            if button.sub_gui is None:
                button.sub_gui = GUI("buildings", (3, 1), box_size=(50, 50), content=[
                    ("power_plant.png", button_callable, [PowerPlant]),
                    ("bank.png", button_callable, [Bank]),
                    ("none.png", button_callable, [None])
                ], output_len=1, parent=button, callback=stick_to_parent, midtop=button.gui.rect.midbottom)
                self.guis.append(button.sub_gui)

        def add_attack_options(button: GUI.GUI_Button):
            if button.sub_gui is None:
                button.sub_gui = GUI("attacks", (7, 1), box_size=(50, 50), content=[
                    ("yes.png", unselect, ()),
                    ("no.png", remove_attack_points, ()),
                    ("back.png", remove_last_point, ()),
                    ("forward.png", add_point, ()),
                    ("select.png", select_vehicle, ()),
                    ("switch.png", toggle_activity, ()),
                    ("none.png", close_gui, ())
                ], output_len=1, parent=button, callback=stick_to_parent, midtop=button.gui.rect.midbottom)
                self.guis.append(button.sub_gui)

        def remove_attack_points(button: GUI.GUI_Button):
            for vehicle in self.selected_vehicles:
                if isinstance(vehicle, Ground_Fire):
                    vehicle: Ground_Fire | Vehicle
                    vehicle.attack_point = None
                elif isinstance(vehicle, Path_Guided_Fire):
                    vehicle.positions.clear()
                    vehicle.launch_permission = False
            self.selected_vehicles.empty()
            close_gui(button)

        def unselect(button: GUI.GUI_Button):
            for vehicle in self.selected_vehicles:
                if isinstance(vehicle, Ground_Fire):
                    vehicle: Ground_Fire | Vehicle
                    vehicle.attack_point = max_reach(vehicle.rect.center, self.pointer.rect.center, vehicle.max_range)
                if isinstance(vehicle, Path_Guided_Fire) and vehicle.positions:
                    vehicle.launch_permission = True

        def select_vehicle(button: GUI.GUI_Button):
            for col_vehicle in point_colliding(self.pointer.rect.center, *self.team.vehicles):
                col_vehicle: pygame.sprite.Sprite | Path_Guided_Fire
                if col_vehicle in self.selected_vehicles:
                    self.selected_vehicles.remove(col_vehicle)
                else:
                    self.selected_vehicles.add(col_vehicle)

        def remove_last_point(button: GUI.GUI_Button):
            for i, vehicle in enumerate(self.selected_vehicles):
                if isinstance(vehicle, Path_Guided_Fire) and vehicle.positions:
                    vehicle: Path_Guided_Fire | Vehicle
                    vehicle.positions.pop()
                    vehicle.launch_permission = False

        def add_point(button: GUI.GUI_Button):
            for i, vehicle in enumerate(self.selected_vehicles):
                if isinstance(vehicle, Path_Guided_Fire):
                    vehicle: Path_Guided_Fire | Vehicle
                    vehicle.positions.append(self.pointer.rect.center)
                    vehicle.launch_permission = False

        def toggle_activity(button: GUI.GUI_Button):
            for vehicle in self.selected_vehicles:
                vehicle: Vehicle
                vehicle.disabled = not vehicle.disabled

        if GUI.find_gui(self.guis, "general") is None:
            self.guis.append(
                GUI("general", (4, 1), parent=self, box_size=(50, 50), callback=stick_to_pointer, content=[
                    ("car.png", add_vehicles, ()),
                    ("house.png", add_buildings, ()),
                    ("attack_point.png", add_attack_options, ()),
                    ("none.png", close_gui, ())
                ], topleft=self.pointer.rect.center))

    def handle_keys(self, **kwargs):
        def draw_ads(team: Team):
            for a_d in team.vehicles:
                if hasattr(a_d, "max_range"):
                    pygame.draw.circle(surface, team.colors, a_d.rect.center, a_d.max_range, 10)

        self.joystick.clear_cache()
        self.pointer.move(pygame.math.Vector2(self.joystick.stick(0, 1)) * 5, relative=True)

        # Draw Effects
        surface = kwargs.get("line_layer")
        for vehicle in self.selected_vehicles:
            vehicle: Ground_Fire | Vehicle
            pygame.draw.rect(surface, (255, 166, 0, 255), vehicle.rect.inflate(7.5, 7.5), 5, border_radius=15)
            if isinstance(vehicle, Ground_Fire):
                vehicle: Ground_Fire | Vehicle
                pygame.draw.line(surface, (255, 255, 0, 180), vehicle.rect.center,
                                 max_reach(vehicle.rect.center, self.pointer.rect.center, vehicle.max_range), 5)
            elif isinstance(vehicle, Path_Guided_Fire) and vehicle.positions:
                vehicle: Path_Guided_Fire | Vehicle
                pygame.draw.lines(surface, (255, 255, 0, 180), False,
                                  (vehicle.rect.center, *vehicle.positions), 5)

        if self.joystick.joystick.get_button(5):
            draw_ads(self.team.enemy_team)

        if self.joystick.joystick.get_button(4):
            draw_ads(self.team)

        if self.in_hand is not None:
            self.in_hand.rect.center = self.pointer.rect.center

        if self.joystick.button_check(7):
            self.create_gui()

        if self.guis:
            if self.joystick.button_check(0):
                self.guis[-1].buttons.cur.data.callback_f()
            if self.joystick.check_dpad(-1, 0):
                self.guis[-1].buttons.previous()
            if self.joystick.check_dpad(1, 0):
                self.guis[-1].buttons.next()
        else:
            if self.joystick.button_check(0):
                if self.in_hand is not None:
                    island = first_overlap(self.in_hand, self.team.island, *self.team.captured_land)
                    island: pygame.sprite.Sprite | Ground
                    if island is not None and not overlapping(self.in_hand, *self.team.vehicles,
                                                              *island.blueprints):
                        self.in_hand.place(island)


class Pilot_Controller(PlayerController):
    def __init__(self, joystick_id, team):
        super().__init__(joystick_id=joystick_id, team=team)
        self.plane = None
        self.plane_bp = pygame.sprite.GroupSingle()
        self.gun_timer = 0
        self.burst = 5
        self.burst_counter = self.burst
        self.last_burst = time.time()

    def handle_keys(self, **kwargs):
        self.joystick.clear_cache()
        if self.plane is not None and self.joystick.joystick is not None:
            self.gun_timer += 1
            if self.plane.over_runway():
                if self.joystick.joystick.get_hat(0) == (0, -1):
                    self.plane.decelerate()
                elif self.joystick.joystick.get_hat(0) == (0, 1):
                    self.plane.accelerate()
            if self.plane.gun is not None:
                if self.joystick.joystick.get_axis(4) > 0.5 and self.gun_timer % 4 == 0 and self.burst_counter > 0:
                    self.fire_gun()
                    self.burst_counter -= 1
                    self.last_burst = time.time()
            if time.time() - self.last_burst >= 3.5:
                self.burst_counter = self.burst
            if self.joystick.trigger_pressed(5):
                self.fire()
            if self.joystick.button_check(3):
                self.plane.flare()  # Needs Timer!
            if self.joystick.button_check(5):
                self.previous_pylon()
            if self.joystick.button_check(4):
                self.next_pylon()
            if self.joystick.button_check(7) and self.plane.landed:
                self.add_gui()
            if self.joystick.button_check(0) and self.plane.landed and self.guis:
                self.guis[-1].buttons.cur.data.callback_f()
            if self.joystick.check_dpad(-1, 0) and self.plane.landed and self.guis:
                self.guis[-1].buttons.previous()
            if self.joystick.check_dpad(1, 0) and self.plane.landed and self.guis:
                self.guis[-1].buttons.next()
        else:
            if self.joystick.button_check(0) and len(self.plane_bp) == 0:
                self.team.spawn_plane()

    def fire(self):
        self.plane.pylons.cur.data.fire()

    def fire_gun(self):
        self.plane.gun.head.data.fire()
        Smoke.add_smoke(self.plane.rect.center, self.plane.v * 1.4, (-0.1, 0.1), (-0.1, 0.1), 0.2)

    def next_pylon(self):
        self.plane.pylons.next()

    def previous_pylon(self):
        self.plane.pylons.previous()

    def flare(self):
        self.plane.flare()

    def next_gui(self):
        self.guis[-1].buttons.next()

    def previous_gui(self):
        self.guis[-1].buttons.previous()

    def add_gui(self):
        def stick_to_plane(gui: GUI):
            gui.set_rect(topleft=self.plane.rect.bottomright)

        def add_to_output(button: GUI.GUI_Button, *args):
            button.gui.output.append(args[0])

        def close_gui(button: GUI.GUI_Button):
            button.gui.destroy()
            self.guis.remove(button.gui)

        def load_pylon(button: GUI.GUI_Button, *args):
            if button.sub_gui is None:
                button.sub_gui = GUI("weapons", (5, 1), [("sidewinder.png", add_to_output, ["sidewinder"]),
                                                         ("bomb.png", add_to_output, ["bomb"]),
                                                         ("jdam.png", add_to_output, ["jdam"]),
                                                         ("harm.png", add_to_output, ["harm"]),
                                                         ("none.png", add_to_output, [None])], output_len=1,
                                     midtop=GUI.find_gui(self.guis, "reload").rect.midbottom)
                self.guis.append(button.sub_gui)
            elif button.sub_gui.done:
                button.gui.parent.load_pylon(args[0], button.sub_gui.output[0])
                self.guis.remove(button.sub_gui)
                button.sub_gui.destroy(done=True)
                button.sub_gui = None

        if len(self.guis) == 0:
            pylons = (("1.png", load_pylon, [0]), ("2.png", load_pylon, [1]), ("3.png", load_pylon, [2]),
                      ("4.png", load_pylon, [3]), ("5.png", load_pylon, [4]))
            self.guis.append(GUI("reload", (self.plane.amount + 1, 1),
                                 [*pylons[0:self.plane.amount], ("none.png", close_gui, [])],
                                 parent=self.plane, callback=stick_to_plane,
                                 topleft=self.plane.rect.bottomright))


class Plane(pygame.sprite.Sprite):
    class Pylon:
        def __init__(self, carrier, offset):
            self.offset = pygame.math.Vector2(offset)
            self.carrier = carrier
            self.item = None
            self.pos = (0, 0)

        def load(self, obj):
            self.item = obj

        def fire(self):
            if self.item:
                self.item.deploy()

        def pos_call(self) -> tuple[float, float]:
            v = self.offset.rotate(self.carrier.angle)
            x = self.carrier.rect.centerx + v.x
            y = self.carrier.rect.centery - v.y
            return x, y

    __slots__ = ('position', 'angle', 'v', 'health', 'stored', 'image', 'rect', 'mask', 'flare_timer', 'pylons')

    size = 0.3

    @classmethod
    def get_idle_image(cls, plane_type, angle=90):
        return pygame.transform.rotozoom(
            pygame.image.load(f"Assets/Planes/{plane_type}.png").convert_alpha(), angle, cls.size
        )

    def __init__(self, team, pos=(0, 0), angle=0, img_path='Assets/Planes/F16.png'):
        super().__init__()
        self.team = team
        self.pos = pygame.math.Vector2(pos)
        self.angle = angle
        self.v = pygame.math.Vector2((0, 0))
        self._health = 100
        self.health = self._health
        self.threats = pygame.sprite.Group()
        self.stored = pygame.image.load(img_path).convert_alpha()
        self.speed = 2
        self.max_speed = 2
        self.image = pygame.transform.rotozoom(self.stored, 0, self.size)
        self.rect = self.image.get_rect(center=self.pos)
        self.mask = pygame.mask.from_surface(self.image)
        self.flare_timer = 0
        self.max_fares = 15
        self.flares = self.max_fares

        team.plane.add(self)

    def kill(self) -> None:
        super(Plane, self).kill()
        self.destroy_pylons()

    def update_image(self):
        self.image = pygame.transform.rotozoom(self.stored, self.angle, self.size)
        self.rect = self.image.get_rect(center=self.pos)
        self.mask = pygame.mask.from_surface(self.image)

    def face_to(self, ang, speed=5.0):
        angle = dir_to(self.rect.center, ang)
        self.angle += math.sin(math.radians(angle - self.angle)) * speed

    def destroy_pylons(self):
        cur = self.pylons.head

        while True:
            pylon = cur.data
            if pylon.item is not None:
                pylon.item.kill()
                pylon.item = None
            cur = cur.next_node
            if cur == self.pylons.head:
                break

    def move(self, amount):
        self.v = pygame.math.Vector2((amount, 0)).rotate(self.angle)
        self.pos.x += self.v[0]
        self.pos.y -= self.v[1]

    def check_out_of_bounds(self):
        if self.rect.right < 0 or self.rect.left > screen.get_width() or \
                self.rect.bottom < 0 or self.rect.top > screen.get_height():
            self.kill()

    def check_health(self):
        if self.health <= 0:
            self.kill()

    def over_runway(self) -> bool:
        return bool(overlapping(self, self.team.runway))

    def accelerate(self) -> None:
        self.speed = min(self.speed + 0.02, self.max_speed)

    def decelerate(self) -> None:
        self.speed = max(self.speed - 0.01, 0)

    def flare(self) -> None:
        if self.flares > 0:
            Flare.add_flare(self.rect.center, self.threats)
            self.flares -= 1


class Player(Plane):
    icon_path = "Player.png"
    price = 150

    class Aim_retical(pygame.sprite.Sprite):
        def __init__(self):
            super().__init__()
            self.pos = (-100, 100)
            self.angle = 0
            self.image = pygame.transform.rotozoom(pygame.image.load('Assets/AimCross.png'), 0, 0.4).convert_alpha()
            self.image.set_alpha(255 / 2)
            self.rect = self.image.get_rect(center=self.pos)

            non_traceables.add(self)

        def update(self):
            self.rect.center = self.pos

    class pylon_indicator(pygame.sprite.Sprite):
        def __init__(self, carrier):
            super().__init__()
            self.surface = pygame.Surface((8, 3)).convert_alpha()
            self.surface.fill("green" if carrier.controller.team.team_num == 0 else "red")
            self.carrier: Player = carrier
            self.image = pygame.transform.rotozoom(self.surface, self.carrier.angle, 1.0)
            self.rect = self.image.get_rect(center=self.carrier.pylons.cur.data.pos_call())

            ui_layer.add(self)

        def update(self):
            self.image = pygame.transform.rotozoom(self.surface, self.carrier.angle, 1.0)
            self.rect = self.image.get_rect(center=self.carrier.pylons.cur.data.pos_call())

    def __init__(self, player_controller, pos, angle=0, plane_type="F16"):
        super().__init__(team=player_controller.team, pos=pos, img_path=f"Assets/Planes/{plane_type}.png")
        self.controller = player_controller
        self.pos = pygame.math.Vector2(pos)
        self.angle = angle
        self.landed = True
        self.max_flares = 15
        self.dmg_range = 35
        self.damage_cache = pygame.sprite.Group()
        self.speed = 0
        self.aim_cross = self.Aim_retical()
        off_sets = {"SU25": (-5, 10, 5, 2, None),
                    "A10": (-1.5, 13, 5, 2, None),
                    "F16": (-10, 19, 3, 2.5, LinkedCircle(self.Pylon(self, (0.0, 0.0)))),
                    "SU27": (-14, 20, 3, 2.5, LinkedCircle(self.Pylon(self, (0.0, 0.0))))}
        x, y, self.amount, self.max_speed, self.gun = off_sets.get(plane_type)
        if self.gun is not None:
            self.load_gun()
        pylons = (self.Pylon(self, (0.0, y * 0)),
                  self.Pylon(self, (x, y * 1)),
                  self.Pylon(self, (x, y * -1)),
                  self.Pylon(self, (x, y * 2)),
                  self.Pylon(self, (x, y * -2)))
        self.pylons = LinkedCircle(*pylons[0:self.amount])
        self.default_layout = (None, None, None, None, None)
        self.reload(*self.default_layout[0:self.amount])

        self.indicator = self.pylon_indicator(self)

        self.life_time = 0

    def kill(self) -> None:
        super(Player, self).kill()
        try:
            if self.gun is not None:
                self.gun.head.data.item.kill()
        except AttributeError:
            pass
        self.controller: Ground_Controller
        self.destroy_guis()
        self.controller.plane = None
        self.aim_cross.kill()
        self.indicator.kill()

    def set_aim_cross(self) -> None:
        item = self.pylons.cur.data.item
        if isinstance(item, Bomb):
            if isinstance(item, JDAM):
                lock = item.lock()
                if lock is not None:
                    self.aim_cross.pos = lock
                    return None
            v = pygame.math.Vector2((item.size - item.detonation_height) / item.drop_speed * self.speed * 0.75,
                                    0).rotate(self.angle)
            pos = self.pylons.cur.data.pos_call()
            self.aim_cross.pos = (pos[0] + v[0], pos[1] - v[1])
        elif isinstance(item, Sidewinder):
            lock = self.pylons.cur.data.item.lock_target()
            if lock is not None:
                self.aim_cross.pos = lock.rect.center
            else:
                self.aim_cross.pos = (-100, -100)
        else:
            self.aim_cross.pos = (-100, -100)

    def next_loaded_pylon(self) -> None:
        starting_pylon = self.pylons.cur
        cur = starting_pylon
        while True:
            cur = cur.next_node
            if cur == starting_pylon:
                break
            if cur.data.item is not None:
                self.pylons.cur = cur

    def reload(self, *weapons):
        self.pylons.cur = self.pylons.head
        for i, weapon in enumerate(weapons):
            self.load_pylon(i, weapon)

    def load_gun(self):
        self.gun.cur.data.load(Gun_Pod(self, self.gun.head, self.team.enemy_team.plane))

    def load_pylon(self, pylon: int, weapon_name: str | None):
        cur = self.pylons.head
        for i in range(pylon):
            cur = cur.next_node
        if cur.data.item is not None:
            cur.data.item.kill()
            self.controller.team.money += cur.data.item.price
            cur.data.item = None
        weapon_dict = {"bomb": (Bomb, (self, cur)),
                       "jdam": (JDAM, (self, cur)),
                       "sidewinder": (Sidewinder, (self, cur, self.team.enemy_team.plane)),
                       # "pod": (Gun_Pod, (self, cur, self.team.enemy_team.plane)),
                       "harm": (Harm, (self, cur)),
                       None: (None, None)
                       }
        weapon, args = weapon_dict.get(weapon_name)
        if weapon is not None and self.controller.team.buy(weapon.price):
            cur.data.load(weapon(*args))

    def face_to(self, ang, speed=5.0):
        if not (0, 0) == ang:
            angle = dir_to((0, 0), ang)
            self.angle += math.sin(math.radians(angle - self.angle)) * speed

    def destroy_guis(self):
        for gui in self.controller.guis:
            gui.destroy(done=True)
        self.controller.guis = []

    def update(self, **kwargs):
        self.life_time += 1
        if self.speed < self.max_speed:
            for explosion in explosion_group:
                if explosion not in self.damage_cache:
                    self.damage_cache.add(explosion)
                    distance = dis_to(self.rect.center, explosion.rect.center)
                    circle_radius = self.dmg_range
                    if distance > circle_radius * 2:
                        continue
                    damage = min(100, max(0, int(-2 * distance + (circle_radius * 4))))
                    self.health -= damage
        if self.health <= 0:
            self.kill()
        if self.over_runway():
            if self.speed == 0 and not self.landed:
                self.landed = True
                self.health = self._health
                if self.gun is not None:
                    self.load_gun()
                self.flares = self.max_flares
            elif self.speed != 0 and self.landed:
                self.landed = False
                self.destroy_guis()
        elif self.life_time > 1:
            if self.speed < self.max_speed:
                self.accelerate()
        self.face_to(self.controller.joystick.stick(0, 1), speed=self.speed / 1.5)
        self.move(self.speed)
        self.check_out_of_bounds()
        self.set_aim_cross()
        self.update_image()


class Ordnance(pygame.sprite.Sprite):
    def __init__(self, carrier, node):
        pygame.sprite.Sprite.__init__(self)
        self.carrier = carrier
        self.node = node
        self.pos = pygame.math.Vector2(self.node.data.pos_call())
        self.angle = self.carrier.angle
        self.size = 0.2
        self.speed = 2
        self.attached = True
        self.stored = pygame.image.load('Assets/Ordnance/bomb.png').convert_alpha()
        self.image = pygame.transform.rotozoom(self.stored, self.angle, self.size)
        self.rect = self.image.get_rect(center=self.pos)
        self.mask = pygame.mask.from_surface(self.image)

        non_traceables.add(self)

    def update_images(self):
        self.image = pygame.transform.rotozoom(self.stored, self.angle, self.size)
        self.rect = self.image.get_rect(center=self.pos)
        self.mask = pygame.mask.from_surface(self.image)

    def check_out_of_bounds(self, f=None):
        if self.rect.right < 0 or self.rect.left > screen.get_width() or \
                self.rect.bottom < 0 or self.rect.top > screen.get_height():
            if f:
                f()
            self.kill()

    def deploy(self):
        self.attached = False
        self.node.data.item = None


class Missile(pygame.sprite.Sprite):
    trash_chance = 0.4
    drag = 0.99

    def __init__(self, controller, pos, target, not_base=True):
        pygame.sprite.Sprite.__init__(self)
        self.controller = controller
        self.pos = pygame.math.Vector2(pos)
        self.size = 1.0
        self.stored = pygame.transform.rotozoom(
            pygame.image.load('Assets/Vehicles/man_aa_missile.png').convert_alpha(),
            0, 0.1)
        self.image = pygame.transform.rotate(self.stored, 0)
        self.rect = self.image.get_rect(center=self.pos)
        self.mask = pygame.mask.from_surface(self.image)

        if target:
            self.target = target
            self.angle = dir_to(self.rect.center, self.target.rect.center)

            if isinstance(self.target, Plane):
                self.target.threats.add(self)

        if not_base:
            self.speed = 3

            self.turn_energy = 50

            self.burner = 90  # Amount of ticks before the missile slows down.

    def predicted_los(self, target, r=0):
        if target:
            t = dis_to(self.rect.center,
                       self.predicted_los(target, r=r + 1) if r <= 2 else target.rect.center) / self.speed
            return target.rect.centerx + (target.v[0] * int(t)), target.rect.centery + (
                    -target.v[1] * int(t))
        else:
            return 0

    def check_for_hit(self):
        for overlap in all_overlaps(self, self.controller.team.enemy_team.plane.sprites()):
            self.remove_threat()
            overlap.health = 0
            self.kill()

    def remove_threat(self):
        try:
            if self.target is not None:
                self.target.threats.remove(self)
        except AttributeError:
            pass

    def check_out_of_bounds(self):
        if self.rect.right < 0 or self.rect.left > screen.get_width() or \
                self.rect.bottom < 0 or self.rect.top > screen.get_height():
            self.remove_threat()
            self.kill()

    def reduce_speed(self, turn):
        if self.burner <= 0:
            self.speed -= abs(turn) / self.turn_energy

    def update_image(self):
        self.image = pygame.transform.rotozoom(self.stored, self.angle, self.size)
        self.rect = self.image.get_rect(center=self.pos)
        self.mask = pygame.mask.from_surface(self.image)

    def slow_down(self, smoke: bool = True, offset: int = -10):
        self.burner -= 1
        if self.burner <= 0:
            self.speed *= self.drag
            if self.speed <= 0.5:
                self.remove_threat()
                self.kill()
        elif smoke:
            v = pygame.math.Vector2((offset, 0)).rotate(self.angle)
            p = self.rect.center
            smoke_vent = (p[0] + v[0], p[1] - v[1])
            Smoke.add_smoke(smoke_vent, spread_x=(-0.2, 0.2), spread_y=(-0.2, 0.2), size=0.1, opacity=122)

    def update(self) -> None:
        self.check_for_hit()
        self.check_out_of_bounds()
        if self.target:
            face_to(self, self.predicted_los(self.target), self.speed, f=self.reduce_speed)
            if gimbal_limit(self, dir_to(self.rect.center, self.target.rect.center), 70):
                self.target = None

        # Slow down the missile
        self.slow_down()

        # Move the missile
        v = pygame.math.Vector2((self.speed, 0)).rotate(self.angle)
        self.pos[0] += v[0]
        self.pos[1] -= v[1]

        # Update
        self.update_image()


class Pod(pygame.sprite.Sprite):
    def __init__(self, carrier, node):
        super().__init__()
        self.carrier = carrier
        self.node = node
        self.pos = pygame.math.Vector2(self.node.data.pos_call())
        self.angle = self.carrier.angle
        self.size = 0.1
        self.ammo_count = 3

        self.stored = pygame.transform.rotozoom(pygame.image.load("Assets/Ordnance/gun_pod.png"), self.angle,
                                                self.size).convert_alpha()
        self.update_image()

        non_traceables.add(self)

    def update_image(self) -> None:
        self.image = pygame.transform.rotozoom(self.stored, self.angle - 90, self.size).convert_alpha()
        self.rect = self.image.get_rect(center=self.node.data.pos_call())

    def deploy(self):
        bomb = Bomb(self.carrier, self.node)
        bomb.attached = False
        non_traceables.add(bomb)
        self.ammo_count -= 1
        if self.ammo_count <= 0:
            self.node.data.item = None
            self.kill()

    def check_out_of_bounds(self, f=None):
        if self.rect.right < 0 or self.rect.left > screen.get_width() or \
                self.rect.bottom < 0 or self.rect.top > screen.get_height():
            if f:
                f()
            self.kill()

    def update(self) -> None:
        self.angle = self.carrier.angle
        self.update_image()
        self.check_out_of_bounds()


class Gun_Pod(Pod):
    price = 10

    class Bullet(pygame.sprite.Sprite):
        def __init__(self, carrier, pos, angle, target_group):
            super().__init__()
            self.pos = pygame.math.Vector2(pos)
            self.angle = angle
            self.target_group = target_group
            self.carrier = carrier
            self.speed = 5
            self.v = pygame.math.Vector2((self.speed, 0)).rotate(self.angle)
            self.image = pygame.transform.rotozoom(pygame.image.load("Assets/bullet.png"), self.angle, 0.2)
            self.rect = self.image.get_rect(center=self.pos)
            self.mask = pygame.mask.from_surface(self.image)

        def check_out_of_bounds(self, f=None):
            if self.rect.right < 0 or self.rect.left > screen.get_width() or \
                    self.rect.bottom < 0 or self.rect.top > screen.get_height():
                if f:
                    f()
                self.kill()

        def update(self):
            self.pos.x += self.v.x
            self.pos.y -= self.v.y
            self.check_out_of_bounds()

            for overlap in all_overlaps(self, self.target_group, exclude=self.carrier):
                self.kill()
                overlap.health -= 20

            self.rect.center = self.pos

    def __init__(self, carrier, node, target_group):
        super().__init__(carrier, node)
        self.ammo_count = 20
        self.target_group = target_group

    def deploy(self):
        if self.ammo_count > -1:
            non_traceables.add(self.Bullet(self.carrier, self.node.data.pos_call(),
                                           self.carrier.angle + random.uniform(-2, 2), self.target_group))
            self.ammo_count -= 1
            if self.ammo_count <= 0:
                self.node.data.item = None
                self.kill()


class Bomb(Ordnance):
    icon_path = "Bomb.png"
    price = 20
    drop_speed = 0.0005

    def __init__(self, carrier, node):
        super().__init__(carrier, node)
        self.stored = pygame.image.load('Assets/Ordnance/bomb.png').convert_alpha()
        self.size = 0.2
        self.detonation_height = 0.14
        self.v = pygame.Vector2((0, 0))

    def deploy(self):
        self.carrier.next_loaded_pylon()
        super().deploy()

    def update(self):
        if self.attached:
            self.pos = pygame.math.Vector2(self.node.data.pos_call())
            self.angle = self.carrier.angle
        else:
            self.v = pygame.math.Vector2(self.carrier.speed * 0.75, 0).rotate(self.angle)
            self.pos.x += self.v[0]
            self.pos.y -= self.v[1]

            if self.carrier.landed:
                self.size = self.detonation_height

            self.size -= self.drop_speed
            if self.size <= self.detonation_height:
                Explosion.add_explosion(self.rect.center)
                self.kill()

        self.update_images()


class JDAM(Bomb):
    icon_path = "JDAM.png"
    price = 45
    max_range = 350.0
    angle_limit = 30.0

    def __init__(self, carrier, node):
        super(JDAM, self).__init__(carrier=carrier, node=node)
        self.stored = pygame.image.load('Assets/Ordnance/jdam.png').convert_alpha()
        self.target_pos = None

    def deploy(self):
        self.carrier.controller.team.ordnances.add(self)
        target = self.lock()
        if target is not None:
            self.target_pos = target
            self.drop_speed = (
                                      self.size - self.detonation_height) / (
                                      dis_to(self.rect.center, self.target_pos) / (self.carrier.speed * 0.75))
        super(JDAM, self).deploy()

    def lock(self) -> tuple[float, float] | None:
        jtacs = tuple(filter(lambda v: isinstance(v, JTAC), self.carrier.controller.team.vehicles))
        d = {}
        for jtac in jtacs:
            if jtac.attack_point is not None and not gimbal_limit(self, dir_to(self.rect.center, jtac.attack_point),
                                                                  self.angle_limit) \
                    and dis_to(self.rect.center, jtac.attack_point) < self.max_range:
                d[dis_to(self.rect.center, jtac.attack_point)] = jtac.attack_point
        if len(d) > 0:
            return d.get(min(d.keys()))

    def update(self):
        if self.target_pos is not None:
            face_to(self, self.target_pos, 1)
        super(JDAM, self).update()


class Sidewinder(Ordnance, Missile):
    icon_path = "Sidewinder.png"
    price = 25
    trash_chance = 0.75
    burner = 45
    speed_multiplier = 2.5
    drag = 0.993
    max_range = 650
    angle_limit = 30.0

    def __init__(self, carrier, node, target_group):
        super().__init__(carrier, node)
        self.stored = pygame.transform.rotozoom(
            pygame.image.load('Assets/Vehicles/man_aa_missile.png').convert_alpha(), 0, 0.1)
        self.size = 0.5
        self.speed = 2
        self.v = pygame.math.Vector2((self.speed, 0))
        self.target_group = target_group
        self.target = None
        self.gimbal_limit = 70

    def predicted_los(self, target, r=0):
        if target:
            t = dis_to(self.rect.center,
                       self.predicted_los(target, r=r + 1) if r <= 2 else target.rect.center) / self.speed
            return target.rect.centerx + (target.v[0] * int(t)), target.rect.centery + (
                    -target.v[1] * int(t))
        else:
            return 0

    def deploy(self):
        self.carrier.controller.team.ordnances.add(self)
        self.attached = False
        self.node.data.item = None
        self.carrier.next_loaded_pylon()
        self.target = self.lock_target()
        self.speed = max(2, self.carrier.speed * self.speed_multiplier)
        if self.target:
            self.target.threats.add(self)

    def lock_target(self):
        return closest_target(self, self.target_group.sprites(), max_range=self.max_range, angle_limit=self.angle_limit)

    def remove_threat(self):
        if self.target:
            self.target.threats.remove(self)

    def check_for_hit(self):
        for overlap in all_overlaps(self, self.target_group.sprites()):
            if overlap is not self.carrier:
                self.remove_threat()
                overlap.health = 0
                self.kill()

    def update(self):
        if self.attached:
            self.pos = pygame.math.Vector2(self.node.data.pos_call())
            self.angle = self.carrier.angle
        else:
            self.check_for_hit()
            self.check_out_of_bounds(f=self.remove_threat)
            if self.target:
                face_to(self, self.predicted_los(self.target), self.speed / 2)
                if gimbal_limit(self, dir_to(self.rect.center, self.target.rect.center), self.gimbal_limit):
                    self.target = None

            # Slow down the missile
            self.slow_down(offset=-8)

            # Move the missile
            self.v = pygame.math.Vector2((self.speed, 0)).rotate(self.angle)
            self.pos[0] += self.v[0]
            self.pos[1] -= self.v[1]

        self.update_images()


class Harm(Ordnance, Missile):
    icon_path = "Harm.png"
    price = 50
    burner = 45.0
    speed_multiplier = 1.33
    drag = 0.996

    def __init__(self, carrier, node):
        super(Harm, self).__init__(carrier=carrier, node=node)
        self.stored = pygame.transform.rotozoom(
            pygame.image.load('Assets/Vehicles/man_aa_missile.png').convert_alpha(), 0, 0.1)
        self.image = self.stored.copy()
        self.rect = self.image.get_rect(center=self.pos)
        self.size = 1.0
        self.burner = 90
        self.v = pygame.math.Vector2((0, 0))
        self.target = None
        self.gimbal_limit = 70

    def deploy(self) -> None:
        self.speed = max(2, self.carrier.speed * self.speed_multiplier)
        self.carrier.controller.team.ordnances.add(self)
        self.attached = False
        self.node.data.item = None
        self.carrier.next_loaded_pylon()
        self.target = self.radar_target()

    def radar_target(self) -> pygame.sprite.Sprite:
        return closest_target(self, self.carrier.controller.team.enemy_team.radars, max_range=750,
                              angle_limit=80)

    def check_for_hit(self):
        for overlap in all_overlaps(self, self.carrier.controller.team.enemy_team.radars):
            overlap.health -= 100
            v = pygame.math.Vector2(((self.rect.width / 2) * 1.5, 0)).rotate(self.angle)
            p = pygame.Vector2(self.rect.center)
            Explosion.add_explosion((p.x + v.x, p.y - v.y))
            self.kill()

    def update(self):
        if self.attached:
            self.pos = pygame.math.Vector2(self.node.data.pos_call())
            self.angle = self.carrier.angle
        else:
            self.check_for_hit()
            self.check_out_of_bounds()
            self.target = self.radar_target()
            if self.target:
                face_to(self, self.target.rect.center, self.speed)

            move(self, self.speed)
            self.slow_down()
        self.update_images()


class Explosion(pygame.sprite.Sprite):
    @classmethod
    def add_explosion(cls, pos):
        explosion_group.add(Explosion(pos))

    def __init__(self, pos):
        super().__init__()
        self.stored = pygame.Surface((1, 1))
        # pygame.transform.rotozoom(pygame.image.load('Assets/effects/explosion_air.png').convert_alpha(), 0, 0.8)
        self.size = 0.2
        self.pos = pos
        self.image = pygame.transform.rotozoom(self.stored, 0, self.size)
        self.rect = self.image.get_rect(midbottom=pos)
        self.opacity = 255

        def reduce_speed(particle: Universal_Particle) -> None:
            particle.v *= 0.95

        step = 24
        for i in range(int(360 / step)):
            non_traceables.add(
                Universal_Particle(
                    "Assets/effects/smoke.png",
                    0.3,
                    random.randint(0, 359),
                    pygame.Vector2((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2))),
                    pygame.Vector2((2, 0)).rotate(i * step),
                    240, 0, 3, run_function=reduce_speed, center=self.rect.center
                )
            )

    def update(self):
        self.image = pygame.transform.rotozoom(self.stored, 0, self.size)
        self.rect = self.image.get_rect(center=self.pos)
        if self.size <= 1:
            self.size += 0.1
        else:
            self.opacity -= 4.5
            self.image.set_alpha(self.opacity)
            if self.opacity <= 0:
                self.kill()


class Smoke(pygame.sprite.Sprite):
    @classmethod
    def add_smoke(cls, pos, m_vec=None, spread_x=(-1, 1), spread_y=(-1, 1), size=0.2, opacity=255, die_speed=5.0):
        non_traceables.add(Smoke(pos, m_vec=m_vec, spread_x=spread_x,
                                 spread_y=spread_y, size=size, opacity=opacity, die_speed=die_speed))

    def __init__(self, pos,
                 m_vec=None,
                 spread_x=(-1, 1),
                 spread_y=(-1, 1),
                 size=0.2,
                 opacity=255,
                 die_speed: int | float = 5):
        super().__init__()
        self.image = pygame.transform.rotozoom(pygame.image.load('Assets/effects/smoke.png').convert_alpha(), 0, size)
        self.pos = pygame.math.Vector2(pos)
        self.rect = self.image.get_rect(center=self.pos)
        self.opacity = opacity
        self.die_speed = die_speed
        self.fall_speed = 0.3
        self.vec = pygame.math.Vector2(random.uniform(spread_x[0], spread_x[1]),
                                       random.uniform(spread_y[0], spread_y[1]))
        self.m_vec = m_vec

    def update(self):
        self.pos[1] += self.fall_speed
        self.pos += self.vec
        if self.m_vec:
            self.pos[0] += self.m_vec[0]
            self.pos[1] -= self.m_vec[1]
        self.rect.center = self.pos
        self.image.set_alpha(self.opacity)
        self.opacity -= self.die_speed
        if self.opacity <= 0:
            self.kill()


class Universal_Particle(pygame.sprite.Sprite):
    @staticmethod
    def place_holder(particle, *args, **kwargs) -> None:
        pass

    def __init__(self, img_path: str,
                 img_size: float,
                 img_rotation: float | int,
                 random_spread: pygame.Vector2,
                 nozzle_vector: pygame.Vector2,
                 start_opacity: int, end_opacity: int, opacity_step: int,
                 init_function=place_holder, init_args: tuple = (),
                 run_function=place_holder, run_args: tuple = (),
                 **kwargs
                 ):
        super(Universal_Particle, self).__init__()
        self.image = pygame.transform.rotozoom(pygame.image.load(img_path).convert_alpha(), img_rotation, img_size)
        self.image.set_alpha(start_opacity)
        self.end_opacity, self.opacity_step = end_opacity, opacity_step
        self.rect = self.image.get_rect(**kwargs)
        self.pos = pygame.Vector2(self.rect.center)
        self.v = random_spread + nozzle_vector

        init_function(self, *init_args)
        self.run_function, self.run_args = run_function, run_args

    def update(self, *args: Any, **kwargs: Any) -> None:
        self.pos.x += self.v.x
        self.pos.y -= self.v.y
        self.rect.center = self.pos
        self.image.set_alpha(self.image.get_alpha() - self.opacity_step)
        if self.image.get_alpha() <= self.end_opacity:
            self.kill()
        self.run_function(self, *self.run_args)


class Flare(pygame.sprite.Sprite):
    @classmethod
    def add_flare(cls, pos, threats):
        non_traceables.add(Flare(pos, threats))

    def __init__(self, pos, carrier_threats):
        super().__init__()
        self.pos = pygame.math.Vector2(pos)
        self.size = 0.5
        self.v = pygame.math.Vector2(random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15))
        self.threats = pygame.sprite.Group()
        self.stored = pygame.image.load('Assets/effects/flares.png').convert_alpha()
        self.image = pygame.transform.rotozoom(self.stored, 0, self.size)
        self.rect = self.image.get_rect(center=pos)
        self.mask = pygame.mask.from_surface(self.image)

        for threat in carrier_threats:
            if random.uniform(0, 1) < threat.trash_chance:
                threat.remove_threat()
                self.threats.add(threat)
                threat.target = self

    def update(self):
        if random.randint(0, 10) == 0:
            Smoke.add_smoke(self.rect.center, size=0.1)

        self.size *= 0.99
        if self.size < 0.1:
            self.kill()
        self.image = pygame.transform.rotozoom(self.stored, 0, self.size)

        self.pos += self.v
        self.rect.center = self.pos


class Blueprint(pygame.sprite.Sprite):
    def __init__(self, controller, obj, args=None, delay: int = 0, free: bool = False, overwrite_image=None):
        super(Blueprint, self).__init__()
        self.assigned_object = obj
        self.controller = controller
        if overwrite_image is None:
            self.image = pygame.transform.flip(
                pygame.Surface.copy(obj.idle),
                flip_x=self.controller.team.team_num == 1,
                flip_y=False)
        else:
            self.image = overwrite_image
        self.image.set_alpha(75)
        fill(self.image, pygame.Color(10, 40, 250))
        self.rect = self.image.get_rect(center=pygame.mouse.get_pos())
        self.mask = pygame.mask.from_surface(self.image)

        self.args = args

        non_traceables.add(self)
        self.timer = delay
        self.free = free
        self.supposed_to_place = False
        self.island = None

    def update(self) -> None:
        if self.supposed_to_place:
            self.timer -= 1
            if self.timer <= 0:
                self.place_object(self.island)

    def place_object(self, island: Ground | Main_Island | Small_Island | None):
        args = self.args if self.args is not None else (self.rect.center, self.controller)
        obj = self.assigned_object(*args)
        if isinstance(obj, Plane):
            self.controller.team.pilot.plane = obj
        if island is not None:
            self.controller.team.vehicles.add(obj)
            island: Ground | pygame.sprite
            island.stationed_vehicles.add(obj)
        self.kill()

    def place(self, island: Ground | Main_Island | Small_Island | None, blueprints=None) -> None:
        if self.free is False:
            if not self.controller.team.buy(self.assigned_object.price):
                return None
        if island is not None:
            self.island = island
            self.island.blueprints.add(self)
        if blueprints is not None:
            blueprints.add(self)
        self.supposed_to_place = True
        if self.controller.in_hand is self:
            self.controller.in_hand = None


class Vehicle(pygame.sprite.Sprite, ABC):
    class Health_Bar(pygame.sprite.Sprite):
        def __init__(self, parent):
            super(Vehicle.Health_Bar, self).__init__()
            self.parent = parent
            self.stored = pygame.image.load("Assets/health_bar.png").convert_alpha()
            self.set_image()

        def render_image(self, value, max_value, color="green") -> pygame.Surface:
            base = pygame.transform.scale(self.stored, (50, 12))
            base_rect = base.get_rect()
            x = (base_rect.width / max_value) * value
            bar = pygame.Surface((x, base_rect.height))
            bar.fill(color)
            bar.set_alpha(75)
            bar_rect = bar.get_rect(midleft=base_rect.midleft)
            base.blit(bar, bar_rect)
            return base

        def set_image(self):
            self.image = self.render_image(max(0, self.parent.health), self.parent.max_health,
                                           "red" if self.parent.disabled else "green")
            self.rect = self.image.get_rect(center=(self.parent.rect.centerx, self.parent.rect.bottom + 10))

        def update(self) -> None:
            if not self.parent.alive():
                self.kill()
            self.set_image()

    idle = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/grad.png').convert_alpha(), 0, 0.1)
    price = 50
    repair_multiplier = 0.85
    repair_cooldown = 360
    delay = 60
    _health = 100

    @abstractmethod
    def __init__(self, controller):
        super().__init__()
        self.life_span = 0
        self.max_health = self._health
        self.health = self.max_health
        self.disabled: bool = False
        self.repair_cooldown_timer = self.repair_cooldown
        self.damage_cache = pygame.sprite.Group()
        self.controller = controller
        self.gui = None
        self.gui_timer = 0
        self.pos = (0, 0)
        self.stored = self.idle.copy()
        self.image = self.stored.copy()
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.update_image()
        ui_layer.add(self.Health_Bar(self))

    @abstractmethod
    def update(self):
        pass

    def set_health(self, value):
        self.max_health = value
        self.health = self.max_health

    def create_health_bar(self):
        non_traceables.add(self.Health_Bar(self))

    def update_image(self):
        self.stored = pygame.transform.flip(self.idle.copy(), flip_x=self.controller.team.team_num == 1, flip_y=False)
        self.image = self.stored.copy()
        self.rect = self.image.get_rect(center=self.pos)
        self.mask = pygame.mask.from_surface(self.image)

    def take_damage(self, dmg_range=30):
        self.repair_cooldown_timer -= 1
        for explosion in explosion_group:
            if explosion not in self.damage_cache:
                self.damage_cache.add(explosion)
                distance = dis_to(self.rect.center, explosion.rect.center)
                circle_radius = dmg_range
                if distance > circle_radius * 2:
                    continue
                damage = min(100, max(0, int(-2 * distance + (circle_radius * 4))))
                self.health -= damage
                self.repair_cooldown_timer = self.repair_cooldown
        if self.health <= 0:
            self.kill()

    def kill(self) -> None:
        super().kill()
        if self.gui is not None:
            self.gui.destroy()

    def spawn_gui_on_click(self):
        def gui_callable(button, *args):
            args0 = args[0]
            button.gui.destroy(done=True)
            match args0:
                case None:
                    button.gui.parent.gui = None
                case 'kill':
                    self.kill()
                case 'move':
                    if self.health == self.max_health:
                        self.kill()
                        self.controller.in_hand = Blueprint(self.controller, type(self), free=True, delay=self.delay)
                        self.controller.in_hand.rect.center = self.controller.pointer.rect.center
                case "repair":
                    if self.repair_cooldown_timer <= 0:
                        price = int((self.health / self.max_health) * (self.price * self.repair_multiplier))
                        if self.controller.team.buy(price):
                            self.health = self.max_health
            self.gui_timer = 10

        self.gui_timer -= 1
        self.life_span += 1
        cons = all((self.controller.joystick is not None,
                    self.controller.joystick.connection,
                    self.controller.in_hand is None,
                    not self.controller.guis,
                    self.gui is None,
                    self.controller.joystick.cache.get(0),
                    self.rect.collidepoint(self.controller.pointer.pos),
                    self.gui is None and self.life_span > 30, self.gui_timer <= 0))
        if cons:
            if GUI.find_gui(self.controller.guis, "vehicle_menu") is None:
                self.controller.guis.append(GUI("vehicle_menu", (1, 4),
                                                content=[
                                                    ("none.png", gui_callable, [None]),
                                                    ("bin.png", gui_callable, ["kill"]),
                                                    ("repair.png", gui_callable, ["repair"]),
                                                    ("move.png", gui_callable, ["move"])
                                                ], parent=self.controller,
                                                topleft=self.rect.bottomright))


class Ground_Fire:
    attack_point: None | pygame.Vector2 = None
    max_range = 500


class Path_Guided_Fire:
    class Path:
        thresh_hold = 50

        def __init__(self, *points):
            if len(points) >= 1:
                self.all = LinkedCircle(*points)
                self.start = self.all.head
                cur = self.all.head
                while True:
                    if cur.next_node == self.start:
                        break
                    cur = cur.next_node
                self.end = cur
            else:
                raise ValueError("Path Must Contain at least 1 item on start")

        def check(self, parent, angle_limit) -> bool:
            parent: Path_Guided_Missile
            if dis_to(parent.pos, self.all.cur.data) < 100 and gimbal_limit(parent,
                                                                            dir_to(parent.pos, self.all.cur.data),
                                                                            angle_limit):
                if self.all.cur.next_node is self.all.head:
                    return True
                self.all.cur = self.all.cur.next_node
                return False

    positions = []
    launch_permission: bool = False


class Building(Vehicle, ABC):
    _health = 150
    income = 0

    @abstractmethod
    def __init__(self, controller):
        super(Building, self).__init__(controller=controller)
        controller.team.buildings.add(self)

    @abstractmethod
    def update(self):
        pass

    def update_image(self):
        self.image = self.idle.copy()
        self.rect = self.image.get_rect(center=self.pos)
        self.mask = pygame.mask.from_surface(self.image)


class Bank(Building):
    idle = pygame.transform.rotozoom(pygame.image.load("Assets/Economy/Bank.png").convert_alpha(), 0, 0.14)
    icon_path = "Bank.png"
    price = 50
    income = 3.5

    _health = 95

    def __init__(self, pos, controller):
        super(Bank, self).__init__(controller=controller)
        self.pos = pygame.Vector2(pos)
        self.update_image()

    def update(self):
        if self.life_span % 30 == 0:
            non_traceables.add(
                Universal_Particle(
                    "Assets/effects/money.png", 0.1, random.uniform(-15, 15),
                    pygame.Vector2((random.uniform(-0.2, 0.2), (random.uniform(0.3, 0.7)))),
                    pygame.Vector2((0, 0)), 255, 0, 1, center=self.rect.center))
        self.take_damage(50)
        self.spawn_gui_on_click()


class PowerPlant(Building):
    idle = pygame.transform.rotozoom(pygame.image.load("Assets/Economy/PowerPlant.png").convert_alpha(), 0, 0.14)
    icon_path = "PowerPlant.png"
    price = 100
    income = 10
    delay = 500
    _health = 150

    def __init__(self, pos, controller):
        super(PowerPlant, self).__init__(controller=controller)
        self.pos = pygame.Vector2(pos)
        self.update_image()

    def update(self):
        self.spawn_gui_on_click()
        self.take_damage(50)
        if self.life_span % 15 == 0:
            Smoke.add_smoke(self.rect.midtop, None, spread_x=(-0.1, 0.1), spread_y=(-1, -0.5),
                            size=0.35, opacity=250, die_speed=1.2)


class Bunker(Building):
    idle = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/bunker.png').convert_alpha(), 0, 0.2)
    icon_path = "Bunker.png"
    price = 0
    _health = 250
    delay = 360

    def __init__(self, pos, controller):
        super().__init__(controller)
        self.pos = pygame.Vector2(pos)
        self.image = pygame.transform.rotozoom(pygame.image.load(
            f'Assets/Vehicles/bunker{controller.team.team_num}.png').convert_alpha(), 0, 0.2)
        self.rect = self.image.get_rect(center=self.pos)
        self.mask = pygame.mask.from_surface(self.image)

    def update_image(self):
        pass

    def update(self):
        self.take_damage(35)
        self.spawn_gui_on_click()

        self.update_image()

    def spawn_gui_on_click(self):
        def gui_callable(button, *args):
            args0 = args[0]
            button.gui.destroy(done=True)
            match args0:
                case None:
                    button.gui.parent.gui = None
                case "repair":
                    if self.repair_cooldown_timer <= 0:
                        price = int((self.health / self.max_health) * (self.price * self.repair_multiplier))
                        if self.controller.team.buy(price):
                            self.health = self.max_health

        self.life_span += 1
        try:
            cons = all((self.controller.joystick is not None,
                        self.controller.joystick.connection,
                        self.controller.in_hand is None,
                        not self.controller.guis,
                        self.gui is None,
                        self.controller.joystick.cache.get(0),
                        self.rect.collidepoint(self.controller.pointer.pos),
                        self.gui is None and self.life_span > 30))
        except AttributeError:
            cons = False
        if cons:
            if GUI.find_gui(self.controller.guis, "vehicle_menu") is None:
                self.controller.guis.append(GUI("vehicle_menu", (1, 2),
                                                content=[
                                                    ("none.png", gui_callable, [None]),
                                                    ("repair.png", gui_callable, ["repair"]),
                                                ], parent=self.controller,
                                                topleft=self.rect.bottomright))


class Radar(Vehicle, ABC):
    max_range = 1200

    @abstractmethod
    def __init__(self, controller):
        super(Radar, self).__init__(controller)
        self.controller.team.radars.add(self)

    def detect_target(self):
        for target in (*self.controller.team.enemy_team.plane, *self.controller.team.enemy_team.ordnances):
            if dis_to(self.rect.center, target.rect.center) <= self.max_range:
                self.controller.team.radar_targets.add(target)


class Medium_Track_Radar(Radar):
    idle = pygame.transform.rotozoom(pygame.image.load("Assets/Vehicles/SA6_TR/idle.png").convert_alpha(), 0, 0.45)
    icon_path = "Mid_Radar.png"
    price = 100
    max_range = 500
    _health = 100

    def __init__(self, pos, controller):
        super().__init__(controller)
        self.base = pygame.image.load("Assets/Vehicles/SA6_TR/base.png").convert_alpha()
        self.radar_org = pygame.image.load("Assets/Vehicles/SA6_TR/radar.png").convert_alpha()
        self.top = pygame.image.load("Assets/Vehicles/SA6_TR/top.png").convert_alpha()

        self.pos = pygame.Vector2(pos)
        self.new_image()
        self.mask = pygame.mask.from_surface(self.image)

    def get_image(self) -> pygame.Surface:
        base = self.base.copy()
        radar = pygame.transform.rotate(self.radar_org.copy(), self.life_span % 360)
        base.blit(radar, radar.get_rect(center=base.get_rect().center))
        base.blit(self.top, self.top.get_rect())
        return base.copy()

    def update_image(self):
        pass

    def new_image(self):
        self.image = pygame.transform.rotozoom(self.get_image(), 0, 0.45)
        self.rect = self.image.get_rect(center=self.pos)

    def update(self):
        self.detect_target()
        self.spawn_gui_on_click()
        self.take_damage(35)

        if self.life_span % 5 == 0:
            self.new_image()


class Search_Radar(Radar):
    idle = pygame.transform.rotozoom(pygame.image.load("Assets/Vehicles/basic_radar.png").convert_alpha(), 0, 0.2)
    icon_path = "SearchRadar.png"
    price = 250
    max_range = 750

    _health = 100

    def __init__(self, pos, controller):
        super(Search_Radar, self).__init__(controller)
        self.pos = pygame.math.Vector2(pos)
        self.image = self.idle.copy()
        self.rect = self.image.get_rect(center=self.pos)
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        self.detect_target()
        self.spawn_gui_on_click()
        self.take_damage(35)

        self.update_image()


class Grad(Vehicle, Ground_Fire):
    __slots__ = ('image', 'rect')
    idle = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/grad.png').convert_alpha(), 0, 0.1)
    icon_path = "Grad.png"
    price = 50.0
    max_range = 600.0
    reload_time = 120
    ammo_cost = 30.0

    class Missile(pygame.sprite.Sprite):
        def __init__(self, controller, pos, target_pos: tuple | pygame.math.Vector2):
            super().__init__()
            self.pos = pygame.math.Vector2(pos)
            self.stored = pygame.image.load('Assets/bullet.png').convert_alpha()
            self.image = self.stored.copy()
            self.rect = self.image.get_rect(center=pos)
            self.mask = pygame.mask.from_surface(self.image)

            # Add randomness to flight path
            target_pos = pygame.math.Vector2(target_pos)
            accuracy = 100
            target_pos += pygame.math.Vector2(
                (random.uniform(-accuracy, accuracy), random.uniform(-accuracy, accuracy))
            )

            self.angle = dir_to(pos, target_pos)
            self.size = 1.0
            self.speed = 5
            self.v = pygame.math.Vector2((self.speed, 0))

            self.expected_flight_time = round(dis_to(self.rect.center, target_pos) / self.speed)
            self.flight_timer = 0

            controller.team.ordnances.add(self)

        def update_image(self):
            self.flight_timer += 1
            if self.flight_timer == self.expected_flight_time:
                self.kill()
                Explosion.add_explosion(self.rect.center)
            self.image = pygame.transform.rotozoom(self.stored, self.angle, self.size)
            self.rect = self.image.get_rect(center=self.pos)

        def update(self):
            move(self, self.speed)
            self.update_image()

    def __init__(self, pos, controller):
        super().__init__(controller)
        self.pos = pos
        self.image = self.idle.copy()
        self.rect = self.image.get_rect(center=pos)
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        self.spawn_gui_on_click()
        self.take_damage(35)
        if self.life_span % self.reload_time == 0 and self.attack_point is not None and self.controller.team.buy(
                self.ammo_cost) and not self.disabled:
            non_traceables.add(
                Grad.Missile(self.controller, self.rect.center, self.attack_point)
            )

        self.update_image()


class Cruise_Missile_Launcher(Vehicle, Path_Guided_Fire):
    idle = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/Patriot.png').convert_alpha(), 0, 0.2)
    icon_path = "Cruise.png"
    price = 500
    reload_time = 600
    ammo_cost = 250

    def __init__(self, pos, controller):
        super().__init__(controller)
        self.pos = pos
        self.mask = None
        self.update_image()
        self.positions = self.positions.copy()

    def update(self):
        self.controller: Ground_Controller
        self.spawn_gui_on_click()
        self.take_damage(35)
        if self.life_span % self.reload_time == 0 and self.launch_permission and self.controller.team.buy(
                self.ammo_cost) and not self.disabled:
            non_traceables.add(Path_Guided_Missile(self.rect.center,
                                                   self.controller,
                                                   Path_Guided_Fire.Path(*self.positions)))
            self.launch_permission = False


class JTAC(Vehicle, Ground_Fire):
    idle = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/jtac.png').convert_alpha(), 0, 0.1)
    max_range = 900
    price = 50

    def __init__(self, pos, controller):
        super().__init__(controller)
        self.pos = pos
        self.image = self.idle.copy()
        self.rect = self.image.get_rect(center=pos)
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        self.spawn_gui_on_click()
        self.take_damage(35)

        self.update_image()


class Command_Centre(Cruise_Missile_Launcher):
    def update(self):
        pass


class SAM(Missile):
    def __init__(self, controller, pos, target, launcher, angle=None):
        super(SAM, self).__init__(controller=controller, pos=pos, target=target)
        self.controller = controller
        self.pos = pygame.math.Vector2(pos)
        self.target = target
        self.org_target = target
        self.launcher = launcher

        self.stored = pygame.image.load('Assets/bullet.png').convert_alpha()
        self.image = self.stored.copy()
        self.rect = self.image.get_rect(center=self.pos)
        self.mask = pygame.mask.from_surface(self.image)

        self.speed = 5
        if angle is None:
            self.angle = dir_to(self.rect.center, self.target.rect.center) if self.target is not None else 0
        else:
            self.angle = angle
        self.total_burner, self.burner = 90, 90
        self.gimbal_limit = 70
        self.drag = 0.995
        self.trash_chance = 0.8

        self.v = pygame.math.Vector2((self.speed, 0))

    def drop_target(self):
        self.launcher.target = None

    def kill(self) -> None:
        super().kill()
        self.drop_target()

    def update(self):
        if self.target is not None and self.target.alive():
            face_to(self, predicted_los(self, self.target, self.speed), self.speed, f=self.reduce_speed)
            if self.target != self.launcher.target:
                self.drop_target()
            hit = first_overlap(self, self.org_target, self.target)
            if hit is not None:
                hit.kill()
                self.kill()
                self.drop_target()
            if self.burner < self.total_burner - 20 and gimbal_limit(
                    self,
                    dir_to(self.rect.center, self.target.rect.center),
                    self.gimbal_limit
            ):
                self.target = None
                self.drop_target()

        self.slow_down()

        move(self, self.speed)
        self.check_out_of_bounds()
        self.update_image()


class Path_Guided_Missile(Missile):
    idle = pygame.image.load("Assets/Vehicles/man_aa_missile.png").convert_alpha()
    speed = 1.5
    turn_speed = 2
    burner = 1500
    drag = 0.99
    _health = 100

    def __init__(self, pos, controller: Ground_Controller, path: Path_Guided_Fire.Path):
        super(Path_Guided_Missile, self).__init__(controller, pos, None, False)
        self.speed = Path_Guided_Missile.speed
        self.burner = Path_Guided_Missile.burner
        self.health = self._health
        self.path = path
        self.angle = dir_to(self.pos, self.path.all.cur.data)
        self.mask = None
        self.update_image()
        self.threats = pygame.sprite.Group()
        self.v = pygame.Vector2((self.speed, 0))

        self.controller.team.ordnances.add(self)
        self.controller.team.plane.add(self)

    def update_image(self):
        self.image = pygame.transform.rotozoom(self.idle.copy(), self.angle, 0.1)
        self.rect = self.image.get_rect(center=self.pos)
        self.mask = pygame.mask.from_surface(self.image)

    def explode(self):
        Explosion.add_explosion(self.rect.center)
        self.kill()

    def update(self, *args: Any, **kwargs: Any) -> None:
        if kwargs.get("plane", False):
            return None
        if self.path.check(self, 90):
            self.explode()
        move(self, self.speed)
        face_to(self, self.path.all.cur.data, self.turn_speed)
        self.slow_down(self.burner % 3 == 0)

        if self.health <= 0:
            self.kill()

        self.update_image()


class Bullet(pygame.sprite.Sprite):
    __slots__ = ('stored', 'position', 'image', 'rect', 'mask', 'v')

    def __init__(self,
                 controller,
                 pos,
                 angle,
                 target,
                 speed: int | float = 5,
                 spread=5,
                 size=0.1,
                 callback: callable = None):
        super().__init__()
        angle += random.uniform(-spread, spread)
        self.stored = pygame.image.load('Assets/bullet.png').convert_alpha()
        self.controller = controller
        self.pos = pygame.math.Vector2(pos)
        self.target = target
        self.callback = callback
        self.image = pygame.transform.rotozoom(self.stored, angle, size)
        self.rect = self.image.get_rect(center=self.pos)
        self.mask = pygame.mask.from_surface(self.image)
        self.v = pygame.math.Vector2((speed, 0)).rotate(angle)

    def update(self):
        self.pos[0] += self.v[0]
        self.pos[1] -= self.v[1]
        self.rect.center = self.pos

        if self.target.alive() and overlapping(self, self.target):
            if self.callback:
                self.callback(self)
            self.kill()

        check_out_of_bounds(self)


class Long_Range_SAM(Vehicle):
    __slots__ = ('image', 'rect')
    idle = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/s300.png').convert_alpha(), 0, 0.35)
    icon_path = "S300.png"
    price = 200
    delay = 360
    max_range = 500
    reload_time = 480
    ammo_cost = Player.price

    class Long_Range_Missile(SAM):
        def __init__(self, controller: Ground_Controller, pos, target, launcher):
            super().__init__(controller, pos, target, launcher)
            self.stored = pygame.transform.rotozoom(
                pygame.image.load("Assets/Vehicles/man_aa_missile.png").convert_alpha(), 0, 0.2
            )
            self.angle = 90
            self.turn_energy = 100

    def __init__(self, pos, controller):
        super().__init__(controller)
        self.size = 0.35
        self.pos = pos
        self.image = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/s300.png').convert_alpha(), 0,
                                               self.size)
        self.rect = self.image.get_rect(center=pos)
        self.mask = pygame.mask.from_surface(self.image)
        self.fire_timer = 0
        self.target = None

        self.controller.team.air_defences.add(self)

    def launch(self, target):
        self.target = target
        x = 30 if self.controller.team.team_num == 1 else -30
        launch_pos = self.rect.center + pygame.math.Vector2((x, 0))
        non_traceables.add(self.Long_Range_Missile(self.controller, launch_pos, self.target, self))

    def update(self):
        self.spawn_gui_on_click()
        self.take_damage(35)
        check_out_of_bounds(self)
        self.fire_timer += 1

        self.update_image()


class Medium_Range_SAM(Vehicle):
    __slots__ = ('image', 'rect')
    idle = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/sa15.png').convert_alpha(), 0, 0.35)
    icon_path = "SA15.png"
    price = 125
    max_range = 380.0
    reload_time = 300
    ammo_cost = round(Player.price / 2)

    class Medium_Range_Missile(SAM):
        def __init__(self, controller: Ground_Controller, pos, target, launcher):
            super().__init__(controller, pos, target, launcher)
            self.stored = pygame.transform.rotozoom(
                pygame.image.load("Assets/Vehicles/man_aa_missile.png").convert_alpha(), 0, 0.12
            )
            self.speed = 4

    def __init__(self, pos, controller):
        super().__init__(controller)
        self.size = 0.35
        self.pos = pos
        self.update_image()
        self.fire_timer = 0
        self.target = None

        self.controller.team.air_defences.add(self)

    def launch(self, target):
        self.target = target
        non_traceables.add(self.Medium_Range_Missile(self.controller, self.rect.center, self.target, self))

    def update(self):
        self.spawn_gui_on_click()
        check_out_of_bounds(self)
        self.take_damage(35)
        self.fire_timer += 1

        self.update_image()


class CWIS(Vehicle):
    idle = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/cwis.png').convert_alpha(), 0, 0.28)
    icon_path = "CWIS.png"
    price = 90
    max_range = 250
    reload_time = 60
    ammo_cost = 5

    def __init__(self, pos, controller):
        super(CWIS, self).__init__(controller=controller)
        self.size = 1.0
        self.pos = pygame.math.Vector2(pos)
        self.update_image()
        self.fire_timer = 0
        self.burst = 0
        self.mag = 15

        self.target = None

        self.controller.team.air_defences.add(self)

    def launch(self, target):
        self.target = target
        self.burst = self.mag

    def fire(self):
        def kill_ord(bullet):
            t = bullet.target
            if not isinstance(t, Player):
                if random.randint(0, 10) == 0:
                    t.kill()

        d = predicted_los(self, self.target, 8)
        non_traceables.add(
            Bullet(self.controller, self.rect.center, dir_to(self.rect.center, d), self.target, size=0.25, spread=1,
                   speed=8, callback=kill_ord)
        )

    def update(self):
        self.spawn_gui_on_click()
        self.take_damage(35)
        self.fire_timer += 1

        if self.burst > 0 and self.target is not None and self.target.alive():
            if self.life_span % 3 == 0:  # Fires one in every x ticks.
                self.fire()
                self.burst -= 1
        elif self.target is not None:
            self.target = None

        self.update_image()


class Vads(Vehicle):
    __slots__ = ('image', 'rect', 'mask', 'target')
    idle = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/vads.png').convert_alpha(), 0, 0.1)
    icon_path = "Vads.png"
    price = 35
    max_range = 250
    ammo_cost = 1

    def __init__(self, pos, controller):
        super().__init__(controller)
        self.image = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/vads.png').convert_alpha(), 0,
                                               0.1)
        self.pos = pos
        self.rect = self.image.get_rect(center=pos)
        self.mask = pygame.mask.from_surface(self.image)
        self.target = None
        self.gui = None

    def predicted_los(self, target, r=0):
        if target:
            t = dis_to(self.rect.center, self.predicted_los(target, r=r + 1) if r <= 2 else target.rect.center) / 5
            return target.rect.centerx + (target.v[0] * int(t)), target.rect.centery + (
                    -target.v[1] * int(t))
        else:
            return 0

    def shoot(self):
        def damage_target(bullet):
            bullet.target.health -= 1

        if self.target and self.controller.team.buy(self.ammo_cost) and not self.disabled:
            non_traceables.add(
                Bullet(self.controller, self.rect.center,
                       dir_to(self.rect.center, self.predicted_los(self.target)), target=self.target,
                       callback=damage_target))

    def update(self):
        self.spawn_gui_on_click()
        self.target = closest_target(self, self.controller.team.enemy_team.plane.sprites(), max_range=self.max_range)
        self.shoot()
        self.take_damage(30)

        self.update_image()


class ManAA(Vehicle):
    class ManAAMissile(Missile):
        trash_chance = 0.75

    idle = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/man_aa.png').convert_alpha(), 0, 0.1)
    icon_path = "ManAA.png"
    price = 75
    max_range = 350
    reload_time = 300
    ammo_cost = 20.0

    def __init__(self, pos, controller):
        super().__init__(controller)
        self.pos = pygame.math.Vector2(pos)
        self.stored = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/man_aa.png').convert_alpha(), 0,
                                                0.1)
        self.image = pygame.transform.rotate(self.stored, 0)
        self.rect = self.image.get_rect(center=self.pos)
        self.mask = pygame.mask.from_surface(self.image)

        self.target = None

        self.fire_timer = 0

    def shoot(self):
        if self.target and not self.disabled:
            non_traceables.add(
                self.ManAAMissile(self.controller, self.pos, self.target)
            )

    def update(self):
        self.spawn_gui_on_click()
        self.target = closest_target(self, self.controller.team.enemy_team.plane.sprites(), max_range=self.max_range)
        self.fire_timer += 1
        if self.target and self.fire_timer % self.reload_time == 0 and self.controller.team.buy(self.ammo_cost):
            self.shoot()
        self.take_damage(40)

        self.update_image()


class Team:
    class TeamUI:
        def __init__(self, team):
            self.team = team
            size = 0.5
            self.weapon_dict = {Bomb: "Dumb Bomb", JDAM: "Guided Bomb", Harm: "Anti Radar", Sidewinder: "AIM9"}
            self.money_counter = UI.Display(ui_layer, size=size, **{0: {"bottomleft": (200, screen.get_height())},
                                                                    1: {"bottomright": (
                                                                        screen.get_width() - 200,
                                                                        screen.get_height())}}.get(
                team.team_num))
            self.money_counter.stored.set_alpha(170)
            self.income_counter = UI.Display(ui_layer, size=size,
                                             **{0: {"midleft": self.money_counter.rect.midright},
                                                1: {"midright": self.money_counter.rect.midleft}}.get(team.team_num))
            self.income_counter.stored.set_alpha(170)
            self.Ord_Display = UI.Display(ui_layer, size=size, **{0: {"midleft": self.income_counter.rect.midright},
                                                                  1: {
                                                                      "midright": self.income_counter.rect.midleft}}.get(
                team.team_num))
            self.Ord_Display.stored.set_alpha(170)
            self.update()

        def get_income(self) -> int | float:
            return sum(building.income for building in self.team.buildings)

        def update(self):
            self.money_counter.display_value(f"{self.team.money}$", font_size=25)
            self.income_counter.display_value(f"{self.get_income()}$", font_size=25)
            weapon = "None"
            if self.team.pilot.plane is not None and self.team.pilot.plane.pylons.cur.data.item is not None:
                weapon = self.weapon_dict.get(type(self.team.pilot.plane.pylons.cur.data.item))
            self.Ord_Display.display_value(f"{weapon}", font_size=16)

    icon_path = "Team.png"
    plane_delay = 300
    plane_price = 150
    money = 1000
    collection_time = 330

    def __init__(self, team_num: int, c: int, p: int, plane_type: str, ground_group: pygame.sprite.Group):
        self.team_num = team_num
        self.colors = {1: (255, 166, 0, 255), 0: (0, 187, 255, 255)}.get(team_num, (221, 0, 255, 255))
        self.pilot = Pilot_Controller(p, self)
        self.controller = Ground_Controller(c, self)
        self.plane_type = plane_type
        self.captured_land = pygame.sprite.Group()

        self.enemy_team: Team | None = None

        self.money_timer = 0

        self.vehicles = pygame.sprite.Group()
        self.buildings = pygame.sprite.Group()
        self.radars = pygame.sprite.Group()
        self.air_defences = pygame.sprite.Group()
        self.radar_targets = pygame.sprite.Group()
        self.attack_points = pygame.sprite.Group()
        self.plane = pygame.sprite.Group()
        self.ordnances = pygame.sprite.Group()

        self.island = Main_Island(self, ground_group)
        self.runway = Runway(self, ground_group)
        self.ui = self.TeamUI(self)

    def buy(self, price) -> bool:
        if self.money - price >= 0:
            self.money -= price
            return True
        return False

    def collect_money(self):
        for building in self.buildings:
            building: PowerPlant | Bank
            self.money += building.income

    def spawn_plane(self):
        p = (99, 738) if self.team_num == 0 else (1821, 738)
        args = (self.pilot, p, 90, self.plane_type)
        plane_bp = Blueprint(self.controller, Player, args=args, delay=self.plane_delay,
                             overwrite_image=Plane.get_idle_image(self.plane_type))
        plane_bp.rect.center = p
        plane_bp.place(None, self.pilot.plane_bp)
        # self.pilot.plane = Player(self.pilot, pos=p, angle=90, plane_type=plane_dict.get(self.team_num))

    def closest_air_defence(self, target):
        no_planes = [CWIS]
        only_planes = [Long_Range_SAM]
        sorted_defences = list(sorted(self.air_defences.sprites(),
                                      key=lambda d: dis_to(d.rect.center, target.rect.center)))
        for a_d in sorted_defences:
            a_d: Long_Range_SAM | Medium_Range_SAM | CWIS
            if a_d.disabled:
                continue
            if isinstance(target, Player) and type(a_d) in no_planes:
                continue
            if not isinstance(target, Player) and type(a_d) in only_planes:
                continue
            if dis_to(a_d.rect.center, target.rect.center) <= a_d.max_range and a_d.fire_timer > a_d.reload_time:
                if self.money - a_d.ammo_cost >= 0:
                    self.money -= a_d.ammo_cost
                    return a_d
        return None

    def target_dealt_with(self, target) -> bool:
        return len(list(filter(lambda a_d: a_d.target == target, self.air_defences.sprites()))) != 0

    def draw(self):
        self.vehicles.draw(screen)
        self.attack_points.draw(screen)
        self.plane.draw(screen)

    def update(self, line_layer):
        self.ui.update()
        self.money_timer += 1
        if self.money_timer % self.collection_time == 0:
            self.collect_money()
        if self.pilot.joystick is not None:
            self.pilot.handle_keys()
        if self.controller is not None and self.controller.joystick is not None and self.controller.joystick.connection:
            self.controller.handle_keys(line_layer=line_layer)
        self.radar_targets.empty()
        self.vehicles.update()
        self.attack_points.update()
        self.plane.update(plane=True)

        for target in self.radar_targets:
            if self.target_dealt_with(target):
                continue
            air_defence = self.closest_air_defence(target)
            if air_defence is not None:
                if air_defence.fire_timer > air_defence.reload_time:
                    air_defence.launch(target)
                    air_defence.fire_timer = 0


gui_group = pygame.sprite.Group()
non_traceables = pygame.sprite.Group()
ui_layer = pygame.sprite.Group()
explosion_group = pygame.sprite.Group()


def main(c0=None, p0=None, c1=None, p1=None, plane0="A10", plane1="SU25") -> int:
    gui_group.empty()
    non_traceables.empty()
    ui_layer.empty()
    explosion_group.empty()

    class Game_UI:
        def __init__(self, t0: Team, t1: Team):
            self.t0, self.t1 = t0, t1
            self.money_ratio = UI.Ratio_Bar(ui_layer, (500, 40), 10,
                                            bottom=screen.get_height() - 50, centerx=screen.get_width() / 2 - 50)
            self.money_ratio.stored.set_alpha(170)
            self.money_label = UI.Label("$", 35, ui_layer, midright=self.money_ratio.rect.midleft)
            self.money_label.image.set_alpha(170)
            self.island_ratio = UI.Ratio_Bar(ui_layer, (500, 40), 10,
                                             midbottom=(self.money_ratio.rect.centerx, self.money_ratio.rect.top - 20))
            self.island_ratio.stored.set_alpha(170)
            self.island_label = UI.Label("Islands", 35, ui_layer, midright=self.island_ratio.rect.midleft)
            self.island_label.image.set_alpha(170)
            self.collection_display = UI.Loading_Box(ui_layer, (100, 100),
                                                     top=self.island_ratio.rect.top,
                                                     left=self.island_ratio.rect.right + 20)
            self.collection_display.stored.set_alpha(170)

            self.update()

        def update(self) -> None:
            self.collection_display.display_decimal(
                (self.t0.money_timer % self.t0.collection_time) / self.t0.collection_time)
            self.money_ratio.display_ratio(self.t0.money / (self.t0.money + self.t1.money))
            r = len(self.t0.captured_land.sprites()) / (
                    len(self.t0.captured_land.sprites()) + len(self.t1.captured_land.sprites()))
            self.island_ratio.display_ratio(r, color_l="Green", color_r="Orange")

    ground_group = pygame.sprite.Group()

    team0 = Team(0, c0, p0, plane0, ground_group)
    team1 = Team(1, c1, p1, plane1, ground_group)

    team0.enemy_team, team1.enemy_team = team1, team0

    team0.captured_land.add(*tuple(Small_Island(team0, (x, y), ground_group) for x, y in ((550, 850), (800, 260))))
    team1.captured_land.add(*tuple(Small_Island(team1, (x, y), ground_group) for x, y in ((1370, 260), (1120, 850))))

    game_ui = Game_UI(team0, team1)

    all_joysticks = tuple(filter(lambda joy: joy is not None,
                                 (team0.controller.joystick, team0.pilot.joystick,
                                  team1.controller.joystick, team1.pilot.joystick)))

    def bunkers_gone(team: Team):
        return len(tuple(filter(lambda sv: isinstance(sv, Bunker), team.island.stationed_vehicles))) == 0

    run_time = 0
    while True:
        run_time += 1

        # Check for Winner

        if run_time > Bunker.delay * 1.5:
            for t in (team0, team1):
                if bunkers_gone(t) and not bunkers_gone(t.enemy_team):
                    return t.enemy_team.team_num
            if bunkers_gone(team0) and bunkers_gone(team1):
                return -1

        # Events
        for event in pygame.event.get():
            match event.type:
                case pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                case pygame.JOYDEVICEREMOVED:
                    for gamepad in all_joysticks:
                        if gamepad.joystick.get_instance_id() == event.instance_id:
                            gamepad.connection = False
                            break
                case pygame.JOYDEVICEADDED:
                    connected_device = pygame.joystick.Joystick(event.device_index)
                    if connected_device.get_name() == "Controller (Xbox 360 Wireless Receiver for Windows)":
                        for gamepad in all_joysticks:
                            if not gamepad.connection:
                                gamepad.connection = True
                                gamepad.joystick = connected_device
                                gamepad.rumble_device = None
                                gamepad.joystick.init()
                                break

        # Clear Layers
        line_layer = pygame.Surface((1920, 1080), pygame.SRCALPHA, 32)

        # Updates
        game_ui.update()
        non_traceables.update()
        ground_group.update()
        ui_layer.update()
        gui_group.update()
        explosion_group.update()
        team0.update(line_layer)
        team1.update(line_layer)

        # Visual
        screen.fill((1, 201, 250))
        ground_group.draw(screen)
        screen.blit(line_layer, (0, 0))
        non_traceables.draw(screen)
        explosion_group.draw(screen)
        team0.draw()
        team1.draw()
        gui_group.draw(screen)
        ui_layer.draw(screen)

        # Text
        draw_on(screen, f"{round(clock.get_fps())}fps")

        # Screen fit
        display.blit(
            pygame.transform.scale(screen, (
                display.get_width(), display.get_width() * screen.get_height() / screen.get_width())),
            (0, 0))

        # Window update
        pygame.display.flip()
        clock.tick(60)


def settings() -> dict[int, Pointer]:
    class Vehicle_Settings:
        class Attribute_changer:
            def __init__(self, pos, obj, attribute: str, step: int | float):
                def change_value(*args):
                    if not args:
                        raise ValueError("A Button was called, but no args were given")
                    self.set_value(max(0.0, self.get_value() + args[0]))
                    self.counter.display_value(self.get_value())

                self.obj = obj
                self.attribute = attribute
                self.counter = UI.Display(ui_group, midright=pos)
                self.counter.display_value(self.get_value())
                self.up_button = UI.Button("next", change_value, button_group, args=(step,), size=(50, 50),
                                           bottomleft=pos)
                self.down_button = UI.Button("previous", change_value, button_group, args=(-step,), size=(50, 50),
                                             topleft=pos)
                self.label = UI.Label(attribute, 50, ui_group, left=self.counter.rect.left,
                                      bottom=self.counter.rect.top)

            def get_value(self) -> int:
                return getattr(self.obj, self.attribute)

            def set_value(self, value: float):
                setattr(self.obj, self.attribute, round(value, 5))

        class Vehicle_Icon(pygame.sprite.Sprite):
            def __init__(self, surface, **kwargs):
                super().__init__()
                self.image = surface
                self.rect = self.image.get_rect(**kwargs)

                ui_group.add(self)

        def __init__(self):
            def button_callable(*args):
                if len(args) == 0:
                    raise ValueError("Not Args were given")
                args_dict = {1: self.vehicles.next, -1: self.vehicles.previous}
                args_dict.get(args[0])()
                self.changer = self.get_changer()
                self.icon = self.get_icon()

            def exit_button_callable():
                self.running = False

            self.vehicles = LinkedCircle(Team,
                                         Player,
                                         Bomb,
                                         JDAM,
                                         Sidewinder,
                                         Harm,
                                         Bank,
                                         PowerPlant,
                                         Bunker,
                                         Search_Radar,
                                         Medium_Track_Radar,
                                         Grad,
                                         Cruise_Missile_Launcher,
                                         Long_Range_SAM,
                                         Medium_Range_SAM,
                                         CWIS,
                                         Vads,
                                         ManAA, )
            self.running = True

            button_c = (960, 950)
            self.next_button = UI.Button("next", button_callable, button_group, args=(1,), midleft=button_c)
            self.previous_button = UI.Button("previous", button_callable, button_group, args=(-1,),
                                             midright=button_c)
            self.exit_button = UI.Button("done", exit_button_callable, button_group,
                                         midleft=self.next_button.rect.midright)
            self.changer = self.get_changer()
            self.icon = self.get_icon()

        def get_icon(self) -> Vehicle_Icon:
            if hasattr(self, "icon") and self.icon is not None:
                self.icon.kill()
            vehicle = self.vehicles.cur.data
            icon = pygame.image.load(f"Assets/Display_icons/{vehicle.icon_path}")
            return self.Vehicle_Icon(icon, midleft=(300, 540))

        def get_changer(self) -> list[Attribute_changer]:
            data = []
            if hasattr(self, "changer") and self.changer:
                for change in self.changer:
                    change.up_button.kill()
                    change.down_button.kill()
                    change.counter.kill()
                    change.label.kill()
            item = self.vehicles.cur.data
            all_atts = (
                ("drop_speed", 0.00001),
                ("trash_chance", 0.05),
                ("burner", 5.0),
                ("speed_multiplier", 0.01),
                ("drag", 0.001),
                ("price", 5.0),
                ("delay", 30.0),
                ("_health", 5.0),
                ("repair_cooldown", 30.0),
                ("repair_multiplier", 0.05),
                ("max_range", 25.0),
                ("angle_limit", 2.5),
                ("reload_time", 10.0),
                ("income", 2.5),
                ("plane_delay", 30.0),
                ("money", 50.0),
                ("collection_time", 30.0),
                ("ammo_cost", 5.0)
            )
            valid_atts = tuple(filter(lambda a: hasattr(item, a[0]), all_atts))
            for j, content in enumerate(valid_atts):
                att, step = content
                data.append((att, step, (450 * (j % 2) + 1200, 160 * math.floor(j / 2) + 160)))
            return [self.Attribute_changer(pos, item, att, step) for att, step, pos in data]

    def add_new_device(device_index: int):
        joy = pygame.joystick.Joystick(device_index)
        if joy.get_name() == "Controller (Xbox 360 Wireless Receiver for Windows)" \
                and joy.get_instance_id() not in gamepads:
            gamepads[joy.get_instance_id()] = Pointer(joy.get_id(), pointer_group, center=(960, 540))

    pointer_group = pygame.sprite.Group()
    button_group = pygame.sprite.Group()
    button_group.add(pygame.sprite.Sprite())
    ui_group = pygame.sprite.Group()

    ui = Vehicle_Settings()

    gamepads = {}

    for i in range(pygame.joystick.get_count()):
        add_new_device(i)
    while ui.running:
        for event in pygame.event.get():
            match event.type:
                case pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                case pygame.JOYDEVICEREMOVED:
                    if event.instance_id in gamepads:
                        pointer = gamepads.get(event.instance_id)
                        pointer.kill()
                        gamepads.pop(event.instance_id)
                case pygame.JOYDEVICEADDED:
                    add_new_device(event.device_index)

        pointer_group.update(button=button_group, joystick=gamepads)
        button_group.update()
        ui_group.update()

        screen.fill((1, 201, 250))
        button_group.draw(screen)
        ui_group.draw(screen)
        pointer_group.draw(screen)

        display.blit(
            pygame.transform.scale(screen, (
                display.get_width(), display.get_width() * screen.get_height() / screen.get_width())),
            (0, 0))

        # Window update
        pygame.display.flip()
        clock.tick(60)

    return gamepads


def start_menu() -> dict:
    class Pad(pygame.sprite.Sprite):
        def __init__(self, pad_id, **kwargs):
            super(Pad, self).__init__()
            self.pad_id = pad_id
            self.image = pygame.Surface((100, 100))
            self.rect = self.image.get_rect(**kwargs)
            self.mask = pygame.mask.from_surface(self.image)

    class Plane_Selector:
        def __init__(self, team_num, buttons, uis, **kwargs):
            def switch_callable():
                self.options.cur = self.options.cur.next_node
                self.display.display_value(self.options.cur.data)

            planes = {0: ("A10", "F16"), 1: ("SU25", "SU27")}.get(team_num)
            self.options = LinkedCircle(*planes)

            self.display = UI.Display(uis, **kwargs)
            self.display.display_value(self.options.cur.data)
            self.button = UI.Button("next", switch_callable, uis, buttons, size=(50, 100),
                                    midleft=self.display.rect.midright)

    gamepads = {}

    def settings_button(joy_dict):
        new_joy = settings()
        kill_inactive_devices(joy_dict)
        for point in new_joy.values():
            add_new_device(point.joystick.joystick.get_id())

    def kill_inactive_devices(joy_dict: dict):
        ids = (pygame.joystick.Joystick(j).get_instance_id() for j in range(pygame.joystick.get_count()))
        removes = []
        for key in joy_dict:
            if key not in ids:
                removes.append(key)
        for key in removes:
            joy_dict.pop(key)

    def add_new_device(device_index: int):
        joy = pygame.joystick.Joystick(device_index)
        if joy.get_name() == "Controller (Xbox 360 Wireless Receiver for Windows)" \
                and joy.get_instance_id() not in gamepads:
            gamepads[joy.get_instance_id()] = Pointer(joy.get_id(), pointer_group, center=(960, 540))

    pointer_group = pygame.sprite.Group()
    pad_group = pygame.sprite.Group(Pad(pad_id="c0", center=(720, 540)),
                                    Pad(pad_id="p0", center=(720, 340)),
                                    Pad(pad_id="c1", center=(1200, 540)),
                                    Pad(pad_id="p1", center=(1200, 340)),
                                    )
    label_group = pygame.sprite.Group()
    for pad in pad_group:
        UI.Label(pad.pad_id, 50, label_group, midright=pad.rect.midleft)
    button_group = pygame.sprite.Group(
        UI.Button("settings", settings_button, args=(gamepads,), center=(960, 950)),
        UI.Button("done", pygame.display.toggle_fullscreen)
    )
    ui_group = pygame.sprite.Group()

    pad_p0 = tuple(filter(lambda p: p.pad_id == "p0", pad_group))[0]
    pad_p1 = tuple(filter(lambda p: p.pad_id == "p1", pad_group))[0]
    switcher0 = Plane_Selector(0, button_group, ui_group, right=pad_p0.rect.left - 150, centery=pad_p0.rect.centery)
    switcher1 = Plane_Selector(1, button_group, ui_group, left=pad_p1.rect.right + 100, centery=pad_p1.rect.centery)

    for i in range(pygame.joystick.get_count()):
        add_new_device(i)

    while True:
        for event in pygame.event.get():
            match event.type:
                case pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                case pygame.JOYDEVICEREMOVED:
                    if event.instance_id in gamepads:
                        pointer = gamepads.get(event.instance_id)
                        pointer.kill()
                        gamepads.pop(event.instance_id)
                case pygame.JOYDEVICEADDED:
                    add_new_device(event.device_index)

        if all(overlapping(pad, *pointer_group) for pad in pad_group):
            r_dict = {}
            for pad in pad_group:
                pad: Pad
                r_dict[pad.pad_id] = first_overlap(pad, *pointer_group).joystick.joystick.get_id()
            r_dict["plane0"] = switcher0.options.cur.data
            r_dict["plane1"] = switcher1.options.cur.data
            return r_dict

        pointer_group.update(joystick=gamepads, button=button_group)
        pad_group.update()

        screen.fill((1, 201, 250))
        pad_group.draw(screen)
        label_group.draw(screen)
        ui_group.draw(screen)
        button_group.draw(screen)
        pointer_group.draw(screen)

        display.blit(
            pygame.transform.scale(screen, (
                display.get_width(), display.get_width() * screen.get_height() / screen.get_width())),
            (0, 0))

        # Window update
        pygame.display.flip()
        clock.tick(60)


def display_winner(winner: int):
    def add_new_device(device_index: int):
        joy = pygame.joystick.Joystick(device_index)
        if joy.get_name() == "Controller (Xbox 360 Wireless Receiver for Windows)" \
                and joy.get_instance_id() not in gamepads:
            gamepads[joy.get_instance_id()] = Pointer(joy.get_id(), pointer_group, center=(960, 540))

    ui_group = pygame.sprite.Group()
    button_group = pygame.sprite.Group()
    pointer_group = pygame.sprite.Group()

    element = UI.Display(ui_group, size=3.0, center=(960, 540))
    text_dict = {-1: "IT'S A DRAW!", 0: "LEFT TEAM WON!", 1: "RIGHT TEAM WON!"}
    element.display_value(text_dict.get(winner), font_size=50)
    exit_button = UI.Button("exit", exit, button_group, right=element.rect.right, top=element.rect.bottom + 50)
    play_button = UI.Button("play", game, button_group, left=element.rect.left, top=element.rect.bottom + 50)

    gamepads = {}

    for i in range(pygame.joystick.get_count()):
        add_new_device(i)

    while True:
        for event in pygame.event.get():
            match event.type:
                case pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                case pygame.JOYDEVICEREMOVED:
                    if event.instance_id in gamepads:
                        pointer = gamepads.get(event.instance_id)
                        pointer.kill()
                        gamepads.pop(event.instance_id)
                case pygame.JOYDEVICEADDED:
                    add_new_device(event.device_index)

        pointer_group.update(button=button_group, joystick=gamepads)

        screen.fill((1, 201, 250))
        ui_group.draw(screen)
        button_group.draw(screen)
        pointer_group.draw(screen)

        display.blit(
            pygame.transform.scale(screen, (
                display.get_width(), display.get_width() * screen.get_height() / screen.get_width())),
            (0, 0))

        # Window update
        pygame.display.flip()
        clock.tick(60)


def game():
    display_winner(main(**start_menu()))


if __name__ == "__main__":
    # start_menu()
    # game()
    Team.money = 10000
    main(c0=0, p1=1, plane1="SU27")
    pygame.quit()
    sys.exit()
