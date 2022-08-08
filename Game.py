import pygame
import math
import time
import random
import sys
from DataStructs import LinkedCircle
from abc import ABC, abstractmethod

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
pygame.init()
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 32, pygame.font.Font.bold)
display = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
screen = pygame.Surface((1920, 1080)).convert_alpha()


def dir_to(mp: tuple[float | int, float | int], tp: tuple[float | int, float | int]) -> float:
    dx = tp[0] - mp[0]
    dy = tp[1] - mp[1]
    rads = math.atan2(-dy, dx)
    rads %= 2 * math.pi
    return math.degrees(rads)


def relative_mouse(m=None) -> tuple[float, float]:
    if m is None:
        m = pygame.mouse.get_pos()
    x = m[0] / (display.get_width() / screen.get_width())
    y = m[1] / (display.get_width() * SCREEN_HEIGHT / SCREEN_WIDTH / screen.get_height())
    return x, y


def round_to_360(x):
    return math.degrees(math.asin(math.sin(math.radians(x))))


def dis_to(mp, tp):
    return math.hypot(mp[0] - tp[0], mp[1] - tp[1])


def face_to(self, ang, turn_limit, f: callable = None):
    angle = dir_to(self.rect.center, ang)
    turn = math.sin(math.radians(angle - self.angle)) * turn_limit
    self.angle += turn
    if f:
        f(turn)


def gimbal_limit(self, angle: int | float, limit: int | float) -> bool:
    """
    Return a bool if the target of the missile is outside its turn radius.
    param self: an object that has an angle attribute.
    param angle: an angle as an integer or float to where the missile is meant to fly.
    param limit: the max. difference in degrees between where the missile is pointed and where it is meant to fly.
    return: bool if the gimbal limit was reached.
    """
    return abs(((self.angle - angle) + 180) % 360 - 180) > limit


def closest_target(self, sprites: list, max_range=250, angle_limit=0, exclude=None):
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


def overlaps_with(self, group: pygame.sprite.Group, exclude=None) -> list:
    """
    The listed passed into the filter call checks rect collisions, then, only the objects
    that are also mask colliding will be keep, the final result will be returned
    """
    r_list = list(filter(lambda obj: self.mask.overlap(obj.mask,
                                                       (obj.rect.x - self.rect.x, obj.rect.y - self.rect.y)),
                         pygame.sprite.spritecollide(self, group, False)))
    if exclude and exclude in r_list:
        r_list.remove(exclude)
    return r_list


def overlap_with_sprite(caller: pygame.sprite.Sprite, sprite: pygame.sprite.Sprite) -> bool:
    if caller.mask.overlap(sprite.mask, (sprite.rect.x - caller.rect.x, sprite.rect.y - caller.rect.y)):
        return True
    return False


def predicted_los(self, target, speed, r=0):
    if target:
        t = dis_to(self.rect.center,
                   predicted_los(self, target, speed, r=r + 1) if r <= 2 else target.rect.center) / speed
        return target.rect.centerx + (target.v[0] * int(t)), target.rect.centery + (
                -target.v[1] * int(t))
    else:
        return 0


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
            self.image = pygame.transform.scale(pygame.image.load(f"Assets/buttons/{filepath}").convert_alpha(),
                                                self.gui.box_size)
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

    def __init__(self, gui_id: str, size: tuple[int, int], content: list[tuple[str, callable, list]] = None,
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
        if content is None:
            self.content = LinkedCircle(("1.png", "Sidewinder"), ("2.png", "Bomb"), ("3.png", 3), ("4.png", 4))
        else:
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
        if str(type(self.parent)) == "<class 'Player_controller.Ground_Controller'>":
            self.parent.guis.remove(self)
        self.kill()

    def set_rect(self, **kwargs):
        self.pos_args = kwargs

    def update(self) -> None:
        if isinstance(self.output_len, int) and len(self.output) >= self.output_len:
            self.done = True
        if self.callback is not None:
            self.callback(self, *self.callback_args)
        self.rect = self.image.get_rect(**self.pos_args)


class Ground(pygame.sprite.Sprite):
    def __init__(self, image_path: str, pos_args: dict):
        super().__init__()
        self.image = pygame.image.load(image_path)
        self.rect = self.image.get_rect(**pos_args)
        self.mask = pygame.mask.from_surface(self.image)


class Island(Ground):
    def __init__(self, side: int):
        """
        :param side: 0 = left side 1 = right side
        """
        pos_args = {"topleft": (0, 0)} if side == 0 else {"topright": (screen.get_width(), 0)}
        super().__init__("Assets/Ground/Island.png", pos_args)

        ground_group.add(self)


class Runway(Ground):
    def __init__(self, side: int):
        """
        :param side: 0 = left side 1 = right side
        """
        pos_args = {"midleft": (50, screen.get_height() / 2)} if side == 0 else {
            "midright": (screen.get_width() - 50, screen.get_height() / 2)}
        super().__init__("Assets/Ground/Runway.png", pos_args)

        ground_group.add(self)


class PlayerController(ABC):
    def __init__(self, joystick_id, team):
        self.joystick = Xbox_Controller(joystick_id)
        self.team = team
        self.guis = []

    @abstractmethod
    def handle_keys(self):
        pass


class Xbox_Controller:
    def __init__(self, joystick_id):
        self.joystick = pygame.joystick.Joystick(joystick_id)
        self.joystick.init()
        self.cache = {}
        self.buttons = {}
        for i in range(self.joystick.get_numbuttons()):
            self.buttons[i] = False
        self.axes = {}
        for i in range(self.joystick.get_numaxes()):
            self.axes[i] = False

    def clear_cache(self):
        self.cache = {}

    def button_check(self, button: int) -> bool:
        if not self.buttons[button]:
            if self.joystick.get_button(button):
                self.buttons[button] = True
                self.cache[button] = True
                return True
        else:
            if self.joystick.get_button(button):
                return False
            else:
                self.buttons[button] = False

    def trigger_pressed(self, axis: int) -> bool:
        if not self.axes[axis]:
            if self.joystick.get_axis(axis) > 0.5:
                self.axes[axis] = True
                return True
        else:
            if self.joystick.get_axis(axis) > 0.5:
                return False
            else:
                self.axes[axis] = False

    def stick(self, axis_x: int, axis_y: int) -> tuple[float, float]:
        dead_zone = 0.2
        if abs(self.joystick.get_axis(axis_x)) < dead_zone:
            x = 0
        else:
            x = self.joystick.get_axis(axis_x)
        if abs(self.joystick.get_axis(axis_y)) < dead_zone:
            y = 0
        else:
            y = -self.joystick.get_axis(axis_y)
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
            pass

    def __init__(self, joystick_id, team):
        super().__init__(joystick_id, team)
        self.pointer = self.Pointer(self)
        self.click = False
        self.lifespan = 0
        self.in_hand = None

    def create_gui(self):
        def stick_to_pointer(gui: GUI):
            gui.set_rect(topleft=self.pointer.rect.center)

        def button_callable(button: GUI.GUI_Button, *args):
            if args[0] is not None:
                self.in_hand = Blueprint(args[0], self)
            button.gui.destroy(done=True)
            self.guis.remove(button.gui)

        if GUI.find_gui(self.guis, "vehicles") is None:
            self.guis.append(GUI("vehicles", (4, 1), box_size=(50, 50), content=[
                ("man_aa.png", button_callable, [ManAA]),
                ("vads.png", button_callable, [Vads]),
                ("grad.png", button_callable, [Grad]),
                ("none.png", button_callable, [None])
            ], output_len=1, parent=self, callback=stick_to_pointer, topleft=self.pointer.rect.center))

    def handle_keys(self):
        self.joystick.clear_cache()
        self.pointer.move(pygame.math.Vector2(self.joystick.stick(1, 0)) * 5, relative=True)
        if self.joystick.button_check(1):
            if self.in_hand is not None:
                self.in_hand.place()

        if self.joystick.button_check(7):
            self.create_gui()

        if self.joystick.button_check(0) and self.guis:
            self.guis[-1].buttons.cur.data.callback_f()
        if self.joystick.button_check(13) and self.guis:
            self.guis[-1].buttons.previous()
        if self.joystick.button_check(11) and self.guis:
            self.guis[-1].buttons.next()


class Pilot_Controller(PlayerController):
    def __init__(self, joystick_id, team):
        super().__init__(joystick_id=joystick_id, team=team)
        self.plane = Player(self, pos=(screen.get_width() / 2, SCREEN_HEIGHT / 2), angle=180)
        self.gun_timer = 25

    def handle_keys(self):
        self.gun_timer += 1
        if self.plane.over_runway():
            if self.joystick.joystick.get_button(12):
                self.plane.decelerate()
            elif self.joystick.joystick.get_button(10):
                self.plane.accelerate()
        if isinstance(self.plane.pylons.cur.data.item, Pod):
            if self.joystick.joystick.get_axis(5) > 0.5 and self.gun_timer > 25:
                self.gun_timer = 0
                self.fire()
        elif isinstance(self.plane.pylons.cur.data.item, Ordnance):
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
        if self.joystick.button_check(13) and self.plane.landed and self.guis:
            self.guis[-1].buttons.previous()
        if self.joystick.button_check(11) and self.plane.landed and self.guis:
            self.guis[-1].buttons.next()

    def fire(self):
        self.plane.pylons.cur.data.fire()

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
                button.sub_gui = GUI("weapons", (1, 4), [("sidewinder.png", add_to_output, ["sidewinder"]),
                                                         ("bomb.png", add_to_output, ["bomb"]),
                                                         ("pod.png", add_to_output, ["pod"]),
                                                         ("none.png", add_to_output, [None])], output_len=1,
                                     midtop=GUI.find_gui(self.guis, "reload").rect.midbottom)
                self.guis.append(button.sub_gui)
            elif button.sub_gui.done:
                button.gui.parent.load_pylon(args[0], button.sub_gui.output[0])
                self.guis.remove(button.sub_gui)
                button.sub_gui.destroy(done=True)
                button.sub_gui = None

        if len(self.guis) == 0:
            self.guis.append(GUI("reload", (6, 1),
                                 [("1.png", load_pylon, [0]), ("2.png", load_pylon, [1]), ("3.png", load_pylon, [2]),
                                  ("4.png", load_pylon, [3]), ("5.png", load_pylon, [4]), ("none.png", close_gui, [])],
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
            x = self.carrier.rect.centerx + v[0]
            y = self.carrier.rect.centery - v[1]
            return x, y

    __slots__ = ('position', 'angle', 'v', 'health', 'stored', 'size', 'image', 'rect', 'mask', 'flare_timer', 'pylons')

    def __init__(self, team, pos=(0, 0), angle=0, img_path='Assets/Planes/F16.png'):
        super().__init__()
        self.team = team
        self.pos = pygame.math.Vector2(pos)
        self.angle = angle
        self.v = pygame.math.Vector2((0, 0))
        self.health = 100
        self.threats = []
        self.stored = pygame.image.load(img_path).convert_alpha()
        self.size = 0.3
        self.speed = 2
        self.image = pygame.transform.rotozoom(self.stored, 0, self.size)
        self.rect = self.image.get_rect(center=self.pos)
        self.mask = pygame.mask.from_surface(self.image)
        self.flare_timer = 0

        team.plane.add(self)

    def update_image(self):
        self.image = pygame.transform.rotozoom(self.stored, self.angle, self.size)
        self.rect = self.image.get_rect(center=self.pos)
        self.mask = pygame.mask.from_surface(self.image)

    def face_to(self, ang, speed=5.0):
        angle = dir_to(self.rect.center, ang)
        self.angle += math.sin(math.radians(angle - self.angle)) * speed

    def destroy(self):
        self.kill()

    def move(self, amount):
        self.v = pygame.math.Vector2((amount, 0)).rotate(self.angle)
        self.pos.x += self.v[0]
        self.pos.y -= self.v[1]

    def check_out_of_bounds(self):
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH or \
                self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT:
            self.destroy()

    def check_health(self):
        if self.health <= 0:
            self.destroy()

    def over_runway(self) -> bool:
        return bool(overlap_with_sprite(self, self.team.runway))

    def accelerate(self) -> None:
        self.speed = min(self.speed + 0.02, 2)

    def decelerate(self) -> None:
        self.speed = max(self.speed - 0.01, 0)

    def flare(self) -> None:
        Flare.add_flare(self.rect.center, self.threats)


class Player(Plane):
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

    def __init__(self, player_controller, pos, angle=0):
        super().__init__(team=player_controller.team, img_path="Assets/Planes/SU25.png")
        self.controller = player_controller
        self.pos = pygame.math.Vector2(pos)
        self.angle = angle
        self.landed = False
        self.aim_cross = self.Aim_retical()
        self.pylons = LinkedCircle(self.Pylon(self, (0.0, 0.0)),
                                   self.Pylon(self, (-5.0, 10.0)),
                                   self.Pylon(self, (-5.0, -10.0)),
                                   self.Pylon(self, (-5.0, 20.0)),
                                   self.Pylon(self, (-5.0, -20.0)))
        self.default_layout = ("Pod", "sidewinder", "sidewinder", "sidewinder", "sidewinder")
        self.reload(*self.default_layout)

    def set_aim_cross(self):
        item = self.pylons.cur.data.item
        if type(item) == Bomb:
            v = pygame.math.Vector2((0.2 - 0.14) / 0.0005 * self.speed * 0.75, 0).rotate(self.angle)
            pos = self.pylons.cur.data.pos_call()
            x = pos[0] + v[0]
            y = pos[1] - v[1]
            self.aim_cross.pos = (x, y)
        elif type(item) == Sidewinder:
            lock = self.pylons.cur.data.item.lock_target()
            if lock is not None:
                self.aim_cross.pos = lock.pos
            else:
                self.aim_cross.pos = (-100, -100)
        elif type(item) == Gun_Pod:
            lock = closest_target(self, self.team.enemy_team.plane.sprites(), max_range=650, angle_limit=90)
            if lock is not None:
                self.aim_cross.pos = predicted_los(self, lock, 5)
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

    def destroy_pylons(self):
        cur = self.pylons.head

        while True:
            pylon = cur.data
            if pylon.item is not None:
                pylon.item.kill()
                pylon.item = None
            cur = cur.next
            if cur == self.pylons.head:
                break

    def reload(self, *weapons):
        self.pylons.cur = self.pylons.head
        for weapon in weapons:
            if self.pylons.cur.data.item is not None:
                self.pylons.cur.data.item.kill()
                self.pylons.cur.data.item = None
            match weapon:
                case "bomb" | "Bomb":
                    self.pylons.cur.data.load(Bomb(self, self.pylons.cur))
                case "sidewinder" | "Sidewinder":
                    self.pylons.cur.data.load(Sidewinder(self, self.pylons.cur, self.team.enemy_team.plane))
                case "pod" | "Pod":
                    self.pylons.cur.data.load(Gun_Pod(self, self.pylons.cur, self.team.enemy_team.plane.sprites()))
                case None:
                    pass
            self.pylons.next()
            if self.pylons.cur == self.pylons.head:
                break

    def load_pylon(self, pylon: int, weapon: str):
        cur = self.pylons.head
        for i in range(pylon):
            cur = cur.next_node
        if cur.data.item is not None:
            cur.data.item.kill()
            cur.data.item = None
        match weapon:
            case "bomb" | "Bomb":
                cur.data.load(Bomb(self, cur))
            case "sidewinder" | "Sidewinder":
                cur.data.load(Sidewinder(self, cur, self.team.enemy_team.plane))
            case "pod" | "Pod":
                cur.data.load(Gun_Pod(self, cur, self.team.enemy_team.plane.sprites()))
            case None:
                pass

    def face_to(self, ang, speed=5.0):
        if not (0, 0) == ang:
            angle = dir_to((0, 0), ang)
            self.angle += math.sin(math.radians(angle - self.angle)) * speed

    def update(self):
        if self.over_runway():
            if self.speed == 0 and not self.landed:
                self.landed = True
            elif self.speed != 0:
                self.landed = False
        else:
            if self.speed < 2:
                self.accelerate()
        self.face_to(self.controller.joystick.stick(1, 0), speed=self.speed * 2.5)
        self.move(self.speed)
        self.check_out_of_bounds()
        self.set_aim_cross()
        self.update_image()


class Ordnance(pygame.sprite.Sprite):
    def __init__(self, carrier, node):
        super().__init__()
        self.carrier = carrier
        self.node = node
        self.pos = pygame.math.Vector2(self.node.data.pos_call())
        self.angle = self.carrier.angle
        self.size = 0.2
        self.speed = 2
        self.attached = True
        self.Ordnance_type = "bomb"
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
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH or \
                self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT:
            if f:
                f()
            self.kill()

    def deploy(self):
        self.attached = False
        self.node.data.item = None


class Pod(pygame.sprite.Sprite):
    def __init__(self, carrier, node):
        super().__init__()
        self.carrier = carrier
        self.node = node
        self.pos = pygame.math.Vector2(self.node.data.pos_call())
        self.angle = self.carrier.angle
        self.size = 0.6
        self.ammo_count = 3

        self.stored = pygame.transform.rotozoom(pygame.image.load("Assets/Ordnance/gun_pod.png"), self.angle,
                                                self.size).convert_alpha()
        self.update_image()

        non_traceables.add(self)

    def update_image(self) -> None:
        self.image = pygame.transform.rotozoom(self.stored, self.angle - 180, self.size).convert_alpha()
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
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH or \
                self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT:
            if f:
                f()
            self.kill()

    def update(self) -> None:
        self.angle = self.carrier.angle
        self.update_image()
        self.check_out_of_bounds()


class Gun_Pod(Pod):
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
            if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH or \
                    self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT:
                if f:
                    f()
                self.kill()

        def update(self):
            self.pos.x += self.v.x
            self.pos.y -= self.v.y
            self.check_out_of_bounds()

            for overlap in overlaps_with(self, self.target_group, exclude=self.carrier):
                self.kill()
                overlap.health -= 20

            self.rect.center = self.pos

    def __init__(self, carrier, node, target_group):
        super().__init__(carrier, node)
        self.ammo_count = 25
        self.target_group = target_group

    def deploy(self):
        if self.ammo_count > -1:
            non_traceables.add(self.Bullet(self.carrier, self.node.data.pos_call(),
                                           self.carrier.angle, self.target_group))
            self.ammo_count -= 1
            if self.ammo_count <= 0:
                self.node.data.item = None
                self.kill()


class Bomb(Ordnance):
    def __init__(self, carrier, node):
        super().__init__(carrier, node)
        self.stored = pygame.image.load('Assets/Ordnance/bomb.png').convert_alpha()
        self.size = 0.2
        self.drop_speed = 0.0005
        self.detonation_height = 0.14

    def deploy(self):
        self.carrier.next_loaded_pylon()
        super().deploy()

    def update(self):
        if self.attached:
            self.pos = pygame.math.Vector2(self.node.data.pos_call())
            self.angle = self.carrier.angle
        else:
            v = pygame.math.Vector2(self.carrier.speed * 0.75, 0).rotate(self.angle)
            self.pos.x += v[0]
            self.pos.y -= v[1]

            if self.carrier.landed:
                self.size = self.detonation_height

            self.size -= self.drop_speed
            if self.size <= self.detonation_height:
                Explosion.add_explosion(self.rect.center)
                self.kill()

        self.update_images()


class Sidewinder(Ordnance):
    def __init__(self, carrier, node, target_group):
        super().__init__(carrier, node)
        self.stored = pygame.transform.rotozoom(
            pygame.image.load('Assets/Vehicles/man_aa_missile.png').convert_alpha(), 0, 0.1)
        self.size = 0.5
        self.Ordnance_type = "aa-missile"
        self.burner = 90
        self.speed = 4
        self.target_group = target_group
        self.target = None
        self.gimbal_limit = 70
        self.trash_chance = 0.05

    def predicted_los(self, target, r=0):
        if target:
            t = dis_to(self.rect.center,
                       self.predicted_los(target, r=r + 1) if r <= 2 else target.rect.center) / self.speed
            return target.rect.centerx + (target.v[0] * int(t)), target.rect.centery + (
                    -target.v[1] * int(t))
        else:
            return 0

    def deploy(self):
        self.attached = False
        self.node.data.item = None
        self.carrier.next_loaded_pylon()
        self.target = self.lock_target()
        if self.target:
            try:
                self.target.threats.append(self)

            except AttributeError:
                pass
            except ValueError:
                pass

    def lock_target(self):
        return closest_target(self, self.target_group, max_range=650, angle_limit=30, exclude=self.carrier)

    def remove_threat(self):
        if self.target:
            try:
                self.target.threats.remove(self)
            except Exception as e:
                print(self.target)
                print(e)

    def check_for_hit(self):
        for overlap in overlaps_with(self, self.target_group.sprites()):
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
                face_to(self, self.predicted_los(self.target), self.speed)
                if gimbal_limit(self, dir_to(self.rect.center, self.target.rect.center), self.gimbal_limit):
                    self.target = None

            # Slow down the missile
            self.burner -= 1
            if self.burner <= 0:
                self.speed *= 0.993
                if self.speed <= 0.5:
                    self.remove_threat()
                    self.kill()
            else:
                Smoke.add_smoke(self.rect.center, spread_x=(-0.2, 0.2), spread_y=(-0.2, 0.2), size=0.1)

            # Move the missile
            v = pygame.math.Vector2((self.speed, 0)).rotate(self.angle)
            self.pos[0] += v[0]
            self.pos[1] -= v[1]

        self.update_images()


class Explosion(pygame.sprite.Sprite):
    @classmethod
    def add_explosion(cls, pos):
        explosion_group.add(Explosion(pos))

    def __init__(self, pos):
        super().__init__()
        self.stored = pygame.transform.rotozoom(pygame.image.load('Assets/effects/explosion_air.png').convert_alpha(),
                                                0, 0.8)
        self.size = 0.1
        self.pos = pos
        self.image = pygame.transform.rotozoom(self.stored, 0, self.size)
        self.rect = self.image.get_rect(midbottom=pos)
        self.opacity = 255

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
    def add_smoke(cls, pos, m_vec=None, spread_x=(-1, 1), spread_y=(-1, 1), size=0.2, opacity=255):
        non_traceables.add(Smoke(pos, m_vec=m_vec, spread_x=spread_x, spread_y=spread_y, size=size, opacity=opacity))

    def __init__(self, pos, m_vec=None, spread_x=(-1, 1), spread_y=(-1, 1), size=0.2, opacity=255):
        super().__init__()
        self.image = pygame.transform.rotozoom(pygame.image.load('Assets/effects/smoke.png').convert_alpha(), 0, size)
        self.pos = pygame.math.Vector2(pos)
        self.rect = self.image.get_rect(center=self.pos)
        self.opacity = opacity
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
        self.opacity -= 5
        if self.opacity <= 0:
            self.kill()


class Flare(pygame.sprite.Sprite):
    @classmethod
    def add_flare(cls, pos, threats):
        non_traceables.add(Flare(pos, threats))

    def __init__(self, pos, carrier_threats):
        super().__init__()
        self.pos = pygame.math.Vector2(pos)
        self.size = 0.5
        self.v = pygame.math.Vector2(random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15))
        self.threats = []
        self.stored = pygame.image.load('Assets/effects/flares.png').convert_alpha()
        self.image = pygame.transform.rotozoom(self.stored, 0, self.size)
        self.rect = self.image.get_rect(center=pos)
        self.mask = pygame.mask.from_surface(self.image)

        for threat in carrier_threats:
            if random.uniform(0, 1) < threat.trash_chance:
                try:
                    threat.remove_threat()
                    self.threats.append(threat)
                    threat.target = self
                except AttributeError:
                    pass
                except ValueError:
                    pass

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
    @classmethod
    def fill(cls, surface, color):
        w, h = surface.get_size()
        r, g, b, _ = color
        for x in range(w):
            for y in range(h):
                a = surface.get_at((x, y))[3]
                surface.set_at((x, y), pygame.Color(r, g, b, a))

    def __init__(self, obj, controller):
        super().__init__()
        self.obj = obj
        self.controller = controller
        self.image = pygame.Surface.copy(obj.idle)
        self.image.set_alpha(75)
        self.fill(self.image, pygame.Color(10, 40, 250))
        self.rect = self.image.get_rect(center=pygame.mouse.get_pos())
        self.mask = pygame.mask.from_surface(self.image)

        non_traceables.add(self)

    def update(self):
        self.rect.center = self.controller.pointer.pos

    def place(self):
        # Place the object represented by the blueprint
        if overlap_with_sprite(self, self.controller.team.island):
            self.controller.team.vehicles.add(self.obj(self.rect.center, self.controller))
            self.controller.in_hand = None
            self.kill()


class Vehicle(pygame.sprite.Sprite):
    idle = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/grad.png').convert_alpha(), 0, 0.1)

    def __init__(self, controller):
        super().__init__()
        self.life_span = 0
        self.controller = controller
        self.gui = None

    def take_damage(self, dmg_range=30):
        for explosion in explosion_group.sprites():
            if dis_to(self.rect.center, explosion.rect.center) < dmg_range:
                self.kill()

    def kill(self) -> None:
        super().kill()
        if self.gui is not None:
            self.gui.destroy()

    def spawn_gui_on_click(self):
        def gui_callable(button, *args):
            if args[0] is None:
                button.gui.destroy(done=True)
                button.gui.parent.gui = None
            elif args[0] == 'kill':
                button.gui.destroy(done=True)
                self.kill()
            elif args[0] == 'move':
                button.gui.destroy(done=True)
                self.kill()
                self.controller.in_hand = Blueprint(type(self), controller=self.controller)
            self.controller.guis.remove(button.gui)

        self.life_span += 1
        if self.controller.joystick.cache.get(1) and self.rect.collidepoint(self.controller.pointer.pos) and \
                self.gui is None and self.life_span > 30:
            if GUI.find_gui(self.controller.guis, "vehicle_menu") is None:
                self.controller.guis.append(GUI("vehicle_menu", (1, 3),
                                                content=[
                                                    ("none.png", gui_callable, [None]),
                                                    ("bin.png", gui_callable, ["kill"]),
                                                    ("move.png", gui_callable, ["move"])
                                                ], parent=self.controller,
                                                topleft=self.rect.bottomright))


class Grad(Vehicle):
    __slots__ = ('image', 'rect')
    idle = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/grad.png').convert_alpha(), 0, 0.1)

    class Missile(pygame.sprite.Sprite):
        def __init__(self, pos):
            super().__init__()
            self.image = pygame.image.load('Assets/bullet.png').convert_alpha()
            self.rect = self.image.get_rect(center=pos)

        def update(self):
            self.rect.x += 1

    def __init__(self, pos, controller):
        super().__init__(controller)
        self.image = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/grad.png').convert_alpha(), 0,
                                               0.1)
        self.rect = self.image.get_rect(center=pos)
        self.mask = pygame.mask.from_surface(self.image)
        self.a = Grad.Missile(self.rect.center)
        non_traceables.add(self.a)

    def update(self):
        self.spawn_gui_on_click()
        self.take_damage(35)


class Vads(Vehicle):
    __slots__ = ('image', 'rect', 'mask', 'target')
    idle = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/vads.png').convert_alpha(), 0, 0.1)

    class VadsBullet(pygame.sprite.Sprite):
        __slots__ = ('stored', 'position', 'image', 'rect', 'mask', 'v')

        def __init__(self, controller, pos, angle):
            super().__init__()
            angle += random.uniform(-5, 5)
            self.stored = pygame.image.load('Assets/bullet.png').convert_alpha()
            self.controller = controller
            self.position = pygame.math.Vector2(pos)
            self.image = pygame.transform.rotozoom(self.stored, angle, 0.1)
            self.rect = self.image.get_rect(center=self.position)
            self.mask = pygame.mask.from_surface(self.image)
            self.v = pygame.math.Vector2((5, 0)).rotate(angle)

        def update(self):
            self.position[0] += self.v[0]
            self.position[1] -= self.v[1]
            self.rect.center = self.position

            for overlap in overlaps_with(self, self.controller.team.enemy_team.plane.sprites()):
                overlap.health -= 1
                self.kill()

            if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH \
                    or self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT:
                self.kill()

    def __init__(self, pos, controller):
        super().__init__(controller)
        self.image = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/vads.png').convert_alpha(), 0,
                                               0.1)
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
        if self.target:
            non_traceables.add(
                self.VadsBullet(self.controller, self.rect.center,
                                dir_to(self.rect.center, self.predicted_los(self.target))))

    def update(self):
        self.spawn_gui_on_click()
        self.target = closest_target(self, self.controller.team.enemy_team.plane.sprites(), max_range=250)
        self.shoot()
        self.take_damage(30)


class ManAA(Vehicle):
    class ManAAMissile(pygame.sprite.Sprite):
        def __init__(self, controller, pos, target):
            super().__init__()
            self.controller = controller
            self.pos = pygame.math.Vector2(pos)
            self.stored = pygame.transform.rotozoom(
                pygame.image.load('Assets/Vehicles/ManAA/missile.png').convert_alpha(),
                0, 0.1)
            self.image = pygame.transform.rotate(self.stored, 0)
            self.rect = self.image.get_rect(center=self.pos)
            self.mask = pygame.mask.from_surface(self.image)

            self.target = target
            self.angle = dir_to(self.rect.center, self.target.rect.center)

            self.target.threats.append(self)

            self.speed = 3

            self.burner = 90  # Amount of ticks before the missile slows down.

            self.trash_chance = 0.4

        def predicted_los(self, target, r=0):
            if target:
                t = dis_to(self.rect.center,
                           self.predicted_los(target, r=r + 1) if r <= 2 else target.rect.center) / self.speed
                return target.rect.centerx + (target.v[0] * int(t)), target.rect.centery + (
                        -target.v[1] * int(t))
            else:
                return 0

        def check_for_hit(self):
            for overlap in overlaps_with(self, self.controller.team.enemy_team.plane.sprites()):
                self.remove_threat()
                overlap.health = 0
                self.kill()

        def remove_threat(self):
            try:
                self.target.threats.remove(self)
            except ValueError:
                pass
            except AttributeError:
                pass

        def check_out_of_bounds(self):
            if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH or \
                    self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT:
                self.remove_threat()
                self.kill()

        def reduce_speed(self, turn):
            if self.burner <= 0:
                self.speed -= abs(turn) / 50

        def update(self) -> None:
            self.check_for_hit()
            self.check_out_of_bounds()
            if self.target:
                face_to(self, self.predicted_los(self.target), self.speed, f=self.reduce_speed)
                if gimbal_limit(self, dir_to(self.rect.center, self.target.rect.center), 70):
                    self.target = None

            # Slow down the missile
            self.burner -= 1
            if self.burner <= 0:
                self.speed *= 0.999
                if self.speed <= 0.5:
                    self.remove_threat()
                    self.kill()
            else:
                v = pygame.math.Vector2(-10, 0).rotate(self.angle)
                p = self.rect.center
                smoke_vent = (p[0] + v[0], p[1] - v[1])
                Smoke.add_smoke(smoke_vent, spread_x=(-0.2, 0.2), spread_y=(-0.2, 0.2), size=0.1, opacity=122)

            # Move the missile
            v = pygame.math.Vector2((self.speed, 0)).rotate(self.angle)
            self.pos[0] += v[0]
            self.pos[1] -= v[1]

            # Update
            self.image = pygame.transform.rotate(self.stored, self.angle)
            self.rect = self.image.get_rect(center=self.pos)
            self.mask = pygame.mask.from_surface(self.image)

    idle = pygame.transform.rotozoom(pygame.image.load('Assets/Vehicles/man_aa.png').convert_alpha(), 0, 0.1)

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
        if self.target:
            non_traceables.add(
                self.ManAAMissile(self.controller, self.pos, self.target)
            )

    def update(self):
        self.spawn_gui_on_click()
        self.target = closest_target(self, self.controller.team.enemy_team.plane.sprites(), max_range=350)
        self.fire_timer += 1
        if self.target and self.fire_timer % 300 == 0:
            self.shoot()
        self.take_damage(40)


class Team:
    def __init__(self, team_num: int):
        self.team_num = team_num
        self.pilot = None
        self.controller = None
        self.island = Island(team_num)
        self.runway = Runway(team_num)

        self.enemy_team = None

        self.vehicles = pygame.sprite.Group()
        self.plane = pygame.sprite.GroupSingle()

    def draw(self):
        self.vehicles.draw(screen)
        self.plane.draw(screen)

    def update(self):
        if self.pilot is not None:
            self.pilot.handle_keys()
        if self.controller is not None:
            self.controller.handle_keys()
        self.vehicles.update()
        self.plane.update()


ground_group = pygame.sprite.Group()
gui_group = pygame.sprite.Group()
non_traceables = pygame.sprite.Group()
explosion_group = pygame.sprite.Group()

team0 = Team(0)
team1 = Team(1)

team0.enemy_team, team1.enemy_team = team1, team0
team0.pilot = Pilot_Controller(2, team0)
team1.pilot = Pilot_Controller(3, team1)


def main():
    last_time = time.time()
    while True:
        # FPS
        frame_time = time.time() - last_time
        last_time = time.time()

        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Updates
        team0.update()
        team1.update()
        non_traceables.update()
        gui_group.update()
        explosion_group.update()

        # Visual
        screen.fill((1, 201, 250))
        ground_group.draw(screen)
        non_traceables.draw(screen)
        explosion_group.draw(screen)
        team0.draw()
        team1.draw()
        gui_group.draw(screen)

        # Text
        screen.blit(font.render(f"{round(frame_time * 1000)}ms", True, (255, 255, 255)), (100, 150))

        # Screen fit
        display.blit(
            pygame.transform.scale(screen, (display.get_width(), display.get_width() * SCREEN_HEIGHT / SCREEN_WIDTH))
            , (0, 0))

        # Window update
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
    pygame.quit()
    sys.exit()
