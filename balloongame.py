# Copyright 2008 by Kate Scheppke and Wade Brainerd.  
# This file is part of Typing Turtle.
#
# Typing Turtle is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Typing Turtle is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Typing Turtle.  If not, see <http://www.gnu.org/licenses/>.

import math
import random, datetime
import pangocairo

from gettext import gettext as _

import gobject, pygtk, gtk, pango

import medalscreen

BALLOON_COLORS = [
    (65535, 0, 0),
    (0, 0, 65535),
    (65535, 32768, 0),
    (0, 32768, 65535),
]

class Balloon:
    def __init__(self, x, y, vx, vy, word):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.word = word
        self.size = max(100, 50 + len(word) * 20) 
        self.color = random.choice(BALLOON_COLORS)

class BalloonGame(gtk.VBox):
    def __init__(self, lesson, activity):
        gtk.VBox.__init__(self)
        
        self.lesson = lesson
        self.activity = activity
        
        # Build title bar.
        title = gtk.Label()
        title.set_markup("<span size='20000'><b>" + lesson['name'] + "</b></span>")
        title.set_alignment(1.0, 0.0)
        
        stoplabel = gtk.Label(_('Go Back'))
        stopbtn =  gtk.Button()
        stopbtn.add(stoplabel)
        stopbtn.connect('clicked', self.stop_cb)
        
        hbox = gtk.HBox()
        hbox.pack_start(stopbtn, False, False, 10)
        hbox.pack_end(title, False, False, 10)
        
        # Build the game drawing area.
        self.area = gtk.DrawingArea()
        self.area.connect("expose-event", self.expose_cb)

        # Connect keyboard grabbing and releasing callbacks.        
        self.area.connect('realize', self.realize_cb)
        self.area.connect('unrealize', self.unrealize_cb)

        self.pack_start(hbox, False, False, 10)
        self.pack_start(self.area, True, True)
        
        self.show_all()
        
        # Initialize the game data.
        self.balloons = []

        self.score = 0
        self.spawn_delay = 10

        self.count = 0
        self.count_left = self.lesson.get('length', 60)

        self.medal = None
        self.finished = False

        # Start the animation loop running.        
        self.update_timer = gobject.timeout_add(20, self.tick, priority=gobject.PRIORITY_HIGH_IDLE+30)
    
    def realize_cb(self, widget):
        self.activity.add_events(gtk.gdk.KEY_PRESS_MASK)
        self.key_press_cb_id = self.activity.connect('key-press-event', self.key_cb)

        # Clear the mouse cursor. 
        #pixmap = gtk.gdk.Pixmap(widget.window, 10, 10)
        #color = gtk.gdk.Color()
        #cursor = gtk.gdk.Cursor(pixmap, pixmap, color, color, 5, 5)
        #widget.window.set_cursor(cursor)
        
    def unrealize_cb(self, widget):
        self.activity.disconnect(self.key_press_cb_id)
    
    def stop_cb(self, widget):
        # Stop the animation loop.
        if self.update_timer:
            gobject.source_remove(self.update_timer)
        
        self.activity.pop_screen()

    def key_cb(self, widget, event):
        # Ignore hotkeys.
        if event.state & (gtk.gdk.CONTROL_MASK | gtk.gdk.MOD1_MASK):
            return False

        # Extract information about the key pressed.
        key = gtk.gdk.keyval_to_unicode(event.keyval)
        if key != 0: key = unichr(key)

        if self.finished:
            key_name = gtk.gdk.keyval_name(event.keyval)
            if key_name == 'Return':
                self.activity.pop_screen()

                # Show the new medal if there was one.
                if self.medal:
                    self.activity.push_screen(medalscreen.MedalScreen(self.medal, self.activity))

        else:
            for b in self.balloons:
                if b.word[0] == key:
                    b.word = b.word[1:]
                    self.add_score(1)

                    # Pop the balloon if it's been typed.
                    if len(b.word) == 0:
                        self.balloons.remove(b)
                        self.add_score(100)

                    self.queue_draw_balloon(b)

                    break
        
        return False
    
    def update_balloon(self, b):
        b.x += b.vx
        b.y += b.vy 

        if b.x < 100 or b.x >= self.bounds.width - 100:
            b.vx = -b.vx

        if b.y < -100:
            self.balloons.remove(b)

        self.queue_draw_balloon(b)
    
    def tick(self):
        if self.finished:
            return

        self.bounds = self.area.get_allocation()
            
        for b in self.balloons:
            self.update_balloon(b)

        self.spawn_delay -= 1
        if self.count_left >= 0 and self.spawn_delay <= 0:
            self.count += 1
            self.count_left -= 1

            word = random.choice(self.lesson['words'])

            x = random.randint(100, self.bounds.width - 100)
            y = self.bounds.height + 100

            vx = random.uniform(-2, 2)
            vy = -2 #random.uniform(-5, -3)

            b = Balloon(x, y, vx, vy, word)
            self.balloons.append(b)

            if self.count < 10:
                delay = 200
            elif self.count < 20:
                delay = 150
            else:
                delay = 100
            self.spawn_delay = random.randint(delay-20, delay+20)

        if self.count_left <= 0 and len(self.balloons) == 0:
            self.finish_game()
 
        return True

    def draw_results(self, cr):
        # Draw background.
        w = self.bounds.width - 400
        h = self.bounds.height - 200
        x = self.bounds.width/2 - w/2
        y = self.bounds.height/2 - h/2

        cr.set_source_rgb(0.762, 0.762, 0.762)
        cr.rectangle(x, y, w, h)
        cr.fill()

        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(x, y, w, h)
        cr.stroke()

        # Draw text
        title = _('You finished!') + '\n'

        pango_cr = pangocairo.CairoContext(cr)
        pango_cr.set_source_rgb(0, 0, 0)
        pango_layout = cr.create_layout()
        pango_layout.set_font_description(pango.FontDescription('Serif Bold 16'))
        pango_layout.set_text(title)
        size = pango_layout.get_size()
        tx = x + (w / 2) - (size[0] / pango.SCALE) / 2
        ty = y + 100
        pango_cr.move_to(tx, ty)
        pango_cr.show_layout(pango_layout)
        pango_cr.stroke()

        report = ''
        report += _('Your score was %(score)d.') % { 'score': self.score } + '\n'
        if self.medal:
            report += _('You earned a %(type)s medal!') % self.medal + '\n'
        report += '\n'
        report += _('Press the ENTER key to continue.')
    
        pango_cr = pangocairo.CairoContext(cr)
        pango_cr.set_source_rgb(0, 0, 0)
        pango_layout = cr.create_layout()
        pango_layout.set_font_description(pango.FontDescription('Times 12'))
        pango_layout.set_text(report)
        size = pango_layout.get_size()
        sx = x + w / 2 - (size[0] / pango.SCALE) / 2
        sy = y + 200
        pango_cr.move_to(sx, sy)
        pango_cr.show_layout(pango_layout)
        pango_cr.stroke()


    def finish_game(self):
        self.finished = True

        # Add to the lesson history.
        report = { 
            'lesson': self.lesson['name'],
            'score': self.score,
        }
        self.activity.add_history(report)

        # Show the medal screen, if one should be given.
        got_medal = None
        
        medals = self.lesson['medals']
        for medal in medals:
            if self.score >= medal['score']:
                got_medal = medal['name']
        
        if got_medal:
            # Award the medal.
            medal = {
                'lesson': self.lesson['name'],
                'type': got_medal,
                'date': datetime.date.today().strftime('%B %d, %Y'),
                'nick': self.activity.nick,
                'score': self.score
            }
            self.medal = medal

            # Compare this medal with any existing medals for this lesson.
            # Only record the best one.
            add_medal = True
            if self.activity.data['medals'].has_key(self.lesson['name']):
                old_medal = self.activity.data['medals'][self.lesson['name']]

                order = ' '.join([m['name'] for m in medals])
                add_idx = order.index(medal['type'])
                old_idx = order.index(old_medal['type']) 

                if add_idx < old_idx:
                    add_medal = False
                elif add_idx == old_idx:
                    if medal['score'] < old_medal['score']:
                        add_medal = False
            
            if add_medal:
                self.activity.data['motd'] = 'newmedal'
                self.activity.data['medals'][self.lesson['name']] = medal
                
                # Refresh the main screen given the new medal.
                self.activity.mainscreen.show_lesson(self.activity.mainscreen.lesson_index)

        self.queue_draw()

    def queue_draw_balloon(self, b):
        x = int(b.x - b.size/2) - 5
        y = int(b.y - b.size/2) - 5
        w = int(b.size + 100)
        h = int(b.size*1.5 + 10)
        self.area.queue_draw_area(x, y, w, h)

    def draw_balloon(self, cr, b):
        x = int(b.x)
        y = int(b.y)

        # Draw the string.
        cr.set_source_rgb(0, 0, 0)
        cr.move_to(int(b.x), int(b.y + b.size / 2))
        cr.line_to(int(b.x), int(b.y + b.size))
        cr.stroke()

        # Draw the balloon.
        cr.save()
        cr.set_source_rgb(b.color[0], b.color[1], b.color[2])
        cr.arc(b.x, b.y, b.size / 2, 0, 2 * math.pi)
        cr.fill()
        cr.restore()

        pango_cr = pangocairo.CairoContext(cr)
        pango_cr.set_source_rgb(0, 0, 0)
        pango_layout = cr.create_layout()
        pango_layout.set_font_description(pango.FontDescription('Sans 12'))
        pango_layout.set_text(unicode(b.word))
        size = pango_layout.get_size()
        x = x - (size[0] / pango.SCALE) / 2
        y = y - (size[1] / pango.SCALE) / 2
        pango_cr.move_to(x, y)
        pango_cr.show_layout(pango_layout)
        pango_cr.stroke()

    def add_score(self, num):
        self.score += num
        self.queue_draw_score()

    def queue_draw_score(self):
        layout = self.area.create_pango_layout(_('SCORE: %d') % self.score)
        layout.set_font_description(pango.FontDescription('Times 14'))    
        size = layout.get_size()
        x = self.bounds.width-20-size[0]/pango.SCALE
        y = 20
        self.queue_draw_area(x, y, x+size[0], y+size[1])

    def draw_score(self, cr):
        pango_cr = pangocairo.CairoContext(cr)
        pango_cr.set_source_rgb(0, 0, 0)
        pango_layout = cr.create_layout()
        pango_layout.set_font_description(pango.FontDescription('Times 14'))
        pango_layout.set_text(_('SCORE: %d') % self.score)
        size = pango_layout.get_size()
        x = self.bounds.width - 20 - size[0] / pango.SCALE
        y = 20
        pango_cr.move_to(x, y)
        pango_cr.show_layout(pango_layout)
        pango_cr.stroke()

    def draw_instructions(self, cr):
        # Draw instructions.
        pango_cr = pangocairo.CairoContext(cr)
        pango_cr.set_source_rgb(0, 0, 0)
        pango_layout = cr.create_layout()
        pango_layout.set_font_description(pango.FontDescription('Times 14'))
        pango_layout.set_text(_('Type the words to pop the balloons!'))
        size = pango_layout.get_size()
        x = (self.bounds.width - size[0] / pango.SCALE) / 2
        y = self.bounds.height - 20 - size[1] / pango.SCALE
        pango_cr.move_to(x, y)
        pango_cr.show_layout(pango_layout)
        pango_cr.stroke()

    def draw(self):
        self.bounds = self.area.get_allocation()

        cr = self.area.window.cairo_create()

        # Draw background.
        cr.set_source_rgb(0.915, 0.915, 1)
        cr.rectangle(0, 0, self.bounds.width, self.bounds.height)
        cr.fill()

        # Draw the balloons.
        for b in self.balloons:
            self.draw_balloon(cr, b)

        if self.finished:
            self.draw_results(cr)

        else:
            self.draw_instructions(cr)

            self.draw_score(cr)

    def expose_cb(self, area, event):
        self.draw()
