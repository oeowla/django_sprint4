from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import Http404
from .models import Post, Category, Comment
from .forms import ProfileEditForm, CommentForm, PostForm
from .utils.pagination import get_paginated_page


class BlogLoginView(LoginView):
    def get_success_url(self):
        return reverse('blog:profile', kwargs={
            'username': self.request.user.username
        })


def index(request):
    posts = Post.objects.published().with_related().with_comment_count(
    ).order_by('-pub_date')
    page_obj = get_paginated_page(posts, request)
    return render(request, 'blog/index.html', {
        'page_obj': page_obj,
    })


def profile_view(request, username):
    profile = get_object_or_404(User, username=username)
    posts = profile.posts.with_comment_count().order_by('-pub_date')
    page_obj = get_paginated_page(posts, request)
    return render(request, 'blog/profile.html', {
        'profile': profile,
        'page_obj': page_obj,
        'user': request.user,
    })


@login_required
def profile_edit_view(request):
    form = ProfileEditForm(request.POST or None, instance=request.user)
    if not form.is_valid():
        return render(request, 'blog/user.html', {'form': form})
    form.save()
    messages.success(request, 'Профиль успешно обновлен!')
    return redirect('blog:profile', username=request.user.username)


@login_required
def create_post(request):
    form = PostForm(request.POST or None, request.FILES or None)
    if not form.is_valid():
        return render(request, 'blog/create.html', {'form': form})
    post = form.save(commit=False)
    post.author = request.user
    post.save()
    messages.success(request, 'Пост успешно создан!')
    return redirect('blog:profile', username=request.user.username)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        messages.error(request, 'Вы можете редактировать только свои публикации')
        return redirect('blog:post_detail', post_id=post.id)
    form = PostForm(request.POST or None, request.FILES or None, instance=post)
    if not form.is_valid():
        return render(request, 'blog/create.html', {'form': form, 'post': post})
    form.save()
    messages.success(request, 'Публикация успешно обновлена!')
    return redirect('blog:post_detail', post_id=post.id)


@login_required
def post_delete(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        messages.error(request, 'Вы можете удалять только свои публикации')
        return redirect('blog:post_detail', post_id=post.id)
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Публикация успешно удалена!')
        return redirect('blog:index')
    form = PostForm(instance=post)
    return render(request, 'blog/create.html', {
        'form': form,
        'post': post
    })


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=post_id)
    if request.user != comment.author:
        messages.error(request, 'Вы можете удалять только свои комментарии')
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        comment.delete()
        messages.success(request, 'Комментарий успешно удален!')
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', {
        'comment': comment,
        'post': comment.post
    })


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if not form.is_valid():
        return redirect('blog:post_detail', post_id=post.id)
    comment = form.save(commit=False)
    comment.post = post
    comment.author = request.user
    comment.save()
    messages.success(request, 'Комментарий успешно добавлен!')
    return redirect('blog:post_detail', post_id=post.id)


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=post_id)
    if request.user != comment.author:
        messages.error(
            request, 'Вы можете редактировать только свои комментарии'
        )
        return redirect('blog:post_detail', post_id=post_id)
    form = CommentForm(request.POST or None, instance=comment)
    if not form.is_valid():
        return render(request, 'blog/comment.html', {
            'comment': comment,
            'form': form,
            'post': comment.post
        })
    form.save()
    messages.success(request, 'Комментарий успешно обновлен!')
    return redirect('blog:post_detail', post_id=post_id)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if not post.is_published:
        if not request.user.is_authenticated or request.user != post.author:
            raise Http404("Пост не найден")
    comments = post.comments.all().order_by('created_at')
    form = CommentForm(request.POST or None)
    if form.is_valid() and request.user.is_authenticated:
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        messages.success(request, 'Ваш комментарий успешно добавлен!')
        return redirect('blog:post_detail', post_id=post.id)
    return render(request, 'blog/detail.html', {
        'post': post,
        'comments': comments,
        'form': form
    })


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )
    posts = category.posts.published().with_comment_count().order_by(
        '-pub_date')
    page_obj = get_paginated_page(posts, request)
    return render(request, 'blog/category.html', {
        'category': category,
        'page_obj': page_obj,
    })
