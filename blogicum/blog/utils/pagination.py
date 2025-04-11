from django.core.paginator import Paginator


def get_paginated_page(objects, request, per_page=10):
    paginator = Paginator(objects, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)