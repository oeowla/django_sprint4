from django.shortcuts import render, get_object_or_404, redirect
from blog.models import Post, Category, Comment
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from .forms import ProfileEditForm, CommentForm, PostForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.urls import reverse
from django.db.models import Count
from django.http import Http404


class CustomLoginView(LoginView):
    def get_success_url(self):
        return reverse('blog:profile', kwargs={
            'username': self.request.user.username
        })


def index(request):
    post_list = Post.objects.published().select_related(
        'author', 'category', 'location'
    ).filter(
        is_published=True,
        category__is_published=True,
        pub_date__lte=timezone.now()
    ).annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'blog/index.html', {
        'page_obj': page_obj,
    })


def profile_view(request, username):
    profile = get_object_or_404(User, username=username)
    posts_list = Post.objects.filter(author=profile).annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')
    paginator = Paginator(posts_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'profile': profile,
        'page_obj': page_obj,
        'user': request.user,
    }
    return render(request, 'blog/profile.html', context)


@login_required
def profile_edit_view(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('blog:profile', username=request.user.username)
    else:
        form = ProfileEditForm(instance=request.user)
    return render(request, 'blog/user.html', {'form': form})


@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, 'Пост успешно создан!')
            return redirect('blog:profile', username=request.user.username)
    else:
        form = PostForm()
    return render(request, 'blog/create.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        messages.error(
            request, 'Вы можете редактировать только свои публикации'
        )
        return redirect('blog:post_detail', post_id=post.id)
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Публикация успешно обновлена!')
            return redirect('blog:post_detail', post_id=post.id)
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/create.html', {
        'form': form,
        'post': post
    })


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
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
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
    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Комментарий успешно обновлен!')
            return redirect('blog:post_detail', post_id=post_id)
    else:
        form = CommentForm(instance=comment)
    return render(request, 'blog/comment.html', {
        'comment': comment,
        'form': form,
        'post': comment.post
    })


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if not post.is_published:
        if not request.user.is_authenticated or request.user != post.author:
            raise Http404("Пост не найден")
    comments = post.comments.all().order_by('created_at')
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(
                request, 'Для комментирования необходимо авторизоваться'
            )
            return redirect('blog:post_detail', post_id=post.id)
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            messages.success(request, 'Ваш комментарий успешно добавлен!')
            return redirect('blog:post_detail', post_id=post.id)
    else:
        comment_form = CommentForm()
    return render(request, 'blog/detail.html', {
        'post': post,
        'comments': comments,
        'form': comment_form
    })


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )
    post_list = category.posts.published().annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'blog/category.html', {
        'category': category,
        'page_obj': page_obj,
        'post_list': page_obj.object_list
    })
