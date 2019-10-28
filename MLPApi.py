# -*- encoding: utf-8 -*-

import sublime
import sublime_plugin

import os.path
from html.parser import HTMLParser

from .lib import markdown2 as md2
from .lib.pre_tables import pre_tables

from .escape_amp import *
from .functions import *
from .setting_names import *
from .image_manager import CACHE_FILE
from random import randint as rnd

__folder__ = os.path.dirname(__file__)


# used to store the phantom's set
windows_phantom_set = {}


def create_preview(window, file_name):
    preview = window.new_file()

    preview.set_name(get_preview_name(file_name))
    preview.set_scratch(True)
    preview.set_syntax_file('Packages/MarkdownLivePreview/.sublime/' + \
                            'MarkdownLivePreviewSyntax.hidden-tmLanguage')

    return preview

def markdown2html(md, basepath, color_scheme):

    # removes/format the YAML/TOML header.
    md = manage_header(md, get_settings().get('header_action'))

    html = '<style>\n{}\n</style>\n'.format(get_style(color_scheme))


    # the option no-code-highlighting does not exists in the official version of markdown2 for now
    # I personaly edited the file (markdown2.py:1743)
    html += md2.markdown(md, extras=['fenced-code-blocks', 'tables', 'strike'])

    # tables aren't supported by the Phantoms
    # This function transforms them into aligned ASCII tables and displays them in a <pre> block
    # (the ironic thing is that they aren't supported either :D)
    html = pre_tables(html)

    # pre block are not supported by the Phantoms.
    # This functions replaces the \n in them with <br> so that it does (1/2)
    html = pre_with_br(html)

    # comments aren't supported by the Phantoms
    # Simply removes them using bs4, so you can be sadic and type `<!-- hey hey! -->`, these one
    # won't be stripped!
    html = strip_html_comments(html)

    # exception, again, because <pre> aren't supported by the phantoms
    # so, because this is monosaped font, I just replace it with a '.' and make transparent ;)
    html = html.replace('&nbsp;', '<i class="space">.</i>')

    # Phantoms have problem with images size when they're loaded from an url/path
    # So, the solution is to convert them to base64

    '''
    img_thread = threading.Thread(target=function_that_downloads, args=some_args)
    img_thread.start()
    '''

    html = replace_img_src_base64(html, basepath=basepath)

    # BeautifulSoup uses the <br/> but the sublime phantoms do not support them...
    html = html.replace('<br/>', '<br />').replace('<hr/>', '<hr />')

    return html

def show_html(md_view, preview):
    global windows_phantom_set
    html = markdown2html(get_view_content(md_view), os.path.dirname(md_view.file_name()), md_view.settings().get('color_scheme'))

    phantom_set = windows_phantom_set.setdefault(preview.window().id(),
                                             sublime.PhantomSet(preview, 'markdown_live_preview'))
    phantom_set.update([sublime.Phantom(sublime.Region(0), html, sublime.LAYOUT_BLOCK,
                                    lambda href: sublime.run_command('open_url', {'url': href}))])

    # lambda href: sublime.run_command('open_url', {'url': href})
    # get the "ratio" of the markdown view's position.
    # 0 < y < 1
    y = md_view.text_to_layout(md_view.sel()[0].begin())[1] / md_view.layout_extent()[1]
    # set the vector (position) for the preview
    vector = [0, y * preview.layout_extent()[1]]
    # remove half of the viewport_extent.y to center it on the screen (verticaly)
    vector[1] -= preview.viewport_extent()[1] / 2
    # make sure the minimum is 0
    vector[1] = 0 if vector[1] < 0 else vector[1]
    # the hide the first line
    vector[1] += preview.line_height()
    preview.set_viewport_position(vector, animate=False)

def clear_cache():
    """Removes the cache file"""
    os.remove(CACHE_FILE)

def release_phantoms_set(view_id=None):
    global windows_phantom_set
    if view_id is None:
        windows_phantom_set = {}
    else:
        del windows_phantom_set[view_id]
