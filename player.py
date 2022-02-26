from cmath import rect
from typing import List, Tuple
from animation import Animator
from GameObjects.equipment import Equipment
import pygame as pg
from pygame.sprite import Group, Sprite
from changed_group import CustomGroup
from settings import IMAGES
from interface import HealthBar
import logger
from timer import Timer
from GameObjects.prefabs import IEffect

log = logger.get_logger(__name__)


# The player class is the main character of the game. It has abilities, weapons, and a set of
# animations
class Player(Sprite):
    mediator = None

    MAX_HP = 100
    HP = MAX_HP

    max_speed = 7.5
    xspeed = 0
    yspeed = 0
    accel = 0.4
    isGodMod = False

    def __init__(self, display_size, mediator, shellGroup: Group, particle_group, *args, **kwargs):
        super().__init__()
        self.HP = Player.MAX_HP
        self.mediator = mediator
        self.health = HealthBar(
            [10, 10], self.HP, self.MAX_HP, [display_size[0]*0.35, display_size[1]*0.02], (240, 84, 84), background=(198, 212, 217), draw_text=True)
        self.animation = Animator()
        self.shellGroup = shellGroup
        self.particle_group = particle_group
        self.equipment = Equipment(self.shellGroup, self.particle_group)
        self.display_size = display_size
        
        self.effectsGroup = EffectsGroup()

        self.images = {
            "default": [pg.image.load(
                IMAGES+'\player\space'+str(i)+'.png').convert_alpha() for i in range(1, 3)],
            "left": [pg.image.load(
                IMAGES+'\player\left'+str(i)+'.png').convert_alpha() for i in range(1, 3)],
            "right": [pg.image.load(
                IMAGES+'\player\\right'+str(i)+'.png').convert_alpha() for i in range(1, 3)]
        }

        self.acting_images = self.images['default']

        self.rect = self.acting_images[0].get_rect(
            center=self.spawn(display_size))
        self.rects = [
            pg.Rect(int(self.rect.left + self.rect.width/2.5), self.rect.top,
                    int(self.rect.width/5), int(self.rect.height*0.9)),
            pg.Rect(self.rect.left, int(self.rect.top +
                    self.rect.height/2.5), self.rect.width, self.rect.height/4)
        ]
        self.direction = pg.Vector2(0.0, 0.0)

    def spawn(self, dispaly_size):
        return (dispaly_size[0] / 2, dispaly_size[1] / 2)

    def updatePosition(self, x_update=None, y_update=None):
        if not (x_update and y_update):
            if (self.rect.left + self.direction.x * self.xspeed > 0) and (self.rect.right + self.direction.x * self.xspeed < self.display_size[0]):
                self.rect.centerx += self.direction.x * self.xspeed

            if (self.rect.bottom + self.direction.y * self.yspeed < self.display_size[1] + 10) and (self.rect.top + self.direction.y * self.yspeed > 0):
                self.rect.centery += self.direction.y * self.yspeed

        self.rects = [
            pg.Rect(int(self.rect.left + self.rect.width/2.5), self.rect.top,
                    int(self.rect.width/5), int(self.rect.height*0.9)),
            pg.Rect(self.rect.left, int(self.rect.top +
                    self.rect.height/2.5), self.rect.width, self.rect.height/4)
        ]

        return self.rect

    def updateActingImage(self, threshold):
        if self.direction.x > threshold:
            self.acting_images = self.images['right']
        elif self.direction.x < -threshold:
            self.acting_images = self.images['left']
        else:
            self.acting_images = self.images['default']

        self.rect = self.acting_images[0].get_rect(center=self.rect.center)

    def increaseAccel(self, axis):
        if axis == 0:
            _direction = self.direction.x
            _speed = self.xspeed
        elif axis == 1:
            _direction = self.direction.y
            _speed = self.yspeed

        if _speed + self.accel < self.max_speed:
            _speed += self.accel

        if axis == 0:
            self.direction.x = _direction
            self.xspeed = _speed
        elif axis == 1:
            self.direction.y = _direction
            self.yspeed = _speed

    def decreaseAccel(self, axis):
        if axis == 0:
            _direction = self.direction.x
            _speed = self.xspeed
        elif axis == 1:
            _direction = self.direction.y
            _speed = self.yspeed

        if _speed - self.accel > 0:
            _speed -= self.accel
        else:
            _speed = 0
            _direction = 0

        if axis == 0:
            self.direction.x = _direction
            self.xspeed = _speed
        elif axis == 1:
            self.direction.y = _direction
            self.yspeed = _speed

    def update(self, *args, **kwargs):
        """Updating all player states"""
        self.effectsGroup.update()
        self.updatePosition()
        self.updateActingImage(threshold=.35)
        self.animation.update(rate=80, frames_len=len(
            self.acting_images), repeat=True)

    def draw(self, dispaly):
        dispaly.blit(
            self.acting_images[self.animation.getIteration], self.rect)
        self.health.draw(dispaly, border_radius=self.rect.height //
                         2, border_top_right_radius=self.rect.height//2)
        self.effectsGroup.draw(dispaly)

    def executeWeapon(self):
        if self.equipment.isUltimateSelected:
            return self.equipment.UseUltimate(self)
        return self.equipment.UseWeapon(self.rect)

    def changeWeapon(self, value=None, update=None):
        return self.equipment.SelectObject(value=value, update=update)

    def selectUltimate(self):
        self.equipment.SelectUltimate(self)

    def getHeal(self, object):  # -> new XP
        """Get size healing from object and use __heal method with healing parameters"""
        return self.__heal()

    def getRects(self):  # -> Rect
        return (self.rect, self.rects)

    def getHealth(self):
        return self.health.HP

    def damage(self, value):
        if not self.isGodMod:
            if self.HP - value > 0:
                self.HP -= value
            else:
                self.HP = 0

            self.health.updateHP(self.HP)

    def AddForce(self, direction: pg.Vector2, force=None, *args, **kwargs):
        _force = force
        if _force is None:
            _force = self.rect.height

        if direction.y > 0 and self.rect.bottom + int(self.rect.height*0.6) + _force > self.display_size[1]:
            direction.y = -1
            return self.AddForce(direction, _force)
        if direction.y < 0 and self.rect.top - int(self.rect.height*0.6) - _force < 0:
            direction.y = 1
            return self.AddForce(direction, _force)
        if direction.x > 0:
            pass
        if direction.x < 0:
            pass

        self.rect.centerx += direction.x * (_force + int(self.rect.width*0.6))
        self.rect.centery += direction.y * (_force + int(self.rect.height*0.6))

        self.direction = direction.normalize()
        self.yspeed = self.max_speed
        self.xspeed = self.max_speed

    def ReactToDamage(self, *args, **kwargs):
        if not self.isGodMod:

            if kwargs.get('enemy_rect') and kwargs.get('direction'):
                if self.rect.centery > kwargs['enemy_rect'].centery:
                    kwargs['direction'].y = 1
                elif self.rect.centery < kwargs['enemy_rect'].centery:
                    kwargs['direction'].y = -1

            self.AddForce(*args, **kwargs)

    def AddEffect(self, effect):
        self.effectsGroup.add(effect)

    def SetGodMode(self, value: bool = None):
        self.isGodMod = value if value is not None else not self.isGodMod

    def restart(self):
        self.__init__(self.display_size, self.mediator,
                      self.shellGroup, self.particle_group)

# -------------------------------------------------------


class EffectsGroup(CustomGroup):
    def __init__(self, *sprites: Tuple[IEffect]):
        super().__init__(*sprites)

    def empty(self):
        for ef in self.sprites():
            pass
        return super().empty()
# -------------------------------------------------------


class MovementLogic:
    def __init__(self, dispay_size, max_speed,  acceleration: float = 1):
        self.direction = pg.Vector2(0, 0)
        self.velocity = pg.Vector2(0, 0)
        self.max_speed = max_speed
        self.acceleration = acceleration
        self.dispay_size = dispay_size

    def UpdatePosition(self, rect, rects, x_update=None, y_update=None):
        if not (x_update and y_update):
            if (rect.left + self.direction.x * self.velocity.x > 0) and (rect.right + self.direction.x * self.velocity.x < self.display_size[0]):
                rect.centerx += self.direction.x * self.velocity.x

            if (rect.bottom + self.direction.y * self.velocity.y < self.display_size[1] + 10) and (rect.top + self.direction.y * self.velocity.y > 0):
                rect.centery += self.direction.y * self.velocity.y

        rects = [
            pg.Rect(int(rect.left + rect.width/2.5), rect.top,
                    int(rect.width/5), int(rect.height*0.9)),
            pg.Rect(rect.left, int(rect.top +
                    rect.height/2.5), rect.width, rect.height/4)
        ]

        return (rect, rects)

    def increaseAccel(self, axis):
        if axis == 0:
            _direction = self.direction.x
            _speed = self.velocity.x
        elif axis == 1:
            _direction = self.direction.y
            _speed = self.velocity.y

        if _speed + self.acceleration < self.max_speed:
            _speed += self.acceleration

        if axis == 0:
            self.direction.x = _direction
            self.velocity.x = _speed
        elif axis == 1:
            self.direction.y = _direction
            self.velocity.y = _speed

    def decreaseAccel(self, axis):
        if axis == 0:
            _direction = self.direction.x
            _speed = self.velocity.x
        elif axis == 1:
            _direction = self.direction.y
            _speed = self.velocity.y

        if _speed - self.acceleration > 0:
            _speed -= self.acceleration
        else:
            _speed = 0
            _direction = 0

        if axis == 0:
            self.direction.x = _direction
            self.velocity.x = _speed
        elif axis == 1:
            self.direction.y = _direction
            self.velocity.y = _speed

    def AddForce(self):
        pass

# -------------------------------------------------------


class ISpaceShip:
    rect: pg.Rect = None
    rects: List[pg.Rect] = []
    acting_images = None

    def __init__(self):
        pass

    def CreateRects(self):
        pass

    def GetRect(self):
        return self.rect

    def GetRects(self):
        return self.rects


class DefaultSpaceShip(ISpaceShip):
    def __init__(self):
        super().__init__()
        self.images = {
            "default": [pg.image.load(
                IMAGES+'\player\space'+str(i)+'.png').convert_alpha() for i in range(1, 3)],
            "left": [pg.image.load(
                IMAGES+'\player\left'+str(i)+'.png').convert_alpha() for i in range(1, 3)],
            "right": [pg.image.load(
                IMAGES+'\player\\right'+str(i)+'.png').convert_alpha() for i in range(1, 3)]
        }
        self.acting_images = self.images.get("default")

    def CreateRects(self, center):
        self.rect = self.acting_images[0].get_rect(center=center)

        self.rects = [
            pg.Rect(int(self.rect.left + self.rect.width/2.5), self.rect.top,
                    int(self.rect.width/5), int(self.rect.height*0.9)),
            pg.Rect(self.rect.left, int(self.rect.top +
                    self.rect.height/2.5), self.rect.width, self.rect.height/4)
        ]
        return super().CreateRects()
