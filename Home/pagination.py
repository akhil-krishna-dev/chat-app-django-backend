from rest_framework.pagination import PageNumberPagination


class MessagePagination(PageNumberPagination):
    page_size = 10

    def paginate_queryset(self, queryset, request, view=None):
        queryset = queryset.order_by('-timestamp')
        return super().paginate_queryset(queryset, request, view)