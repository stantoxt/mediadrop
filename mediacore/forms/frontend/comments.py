# This file is a part of MediaCore, Copyright 2009 Simple Station Inc.
#
# MediaCore is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MediaCore is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from tw.forms import TextField, TextArea
from tw.forms.validators import NotEmpty
from tw.api import WidgetsList

from mediacore.forms import ListForm, SubmitButton


class PostCommentForm(ListForm):
    template = 'mediacore.templates.comments.post'
    id = 'post-comment-form'
    css_class = 'form'

    class fields(WidgetsList):
        name = TextField(validator=NotEmpty)
        body = TextArea(validator=NotEmpty, label_text='Comment', attrs=dict(rows=5, cols=25))
        submit = SubmitButton(default='Post Comment', css_class='btn btn-post-comment')


