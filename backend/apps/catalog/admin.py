from django.contrib import admin

from .models import ExternalProductMapping, Product, ProductGroup, ProductSubgroup


@admin.register(ProductGroup)
class ProductGroupAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo")


@admin.register(ProductSubgroup)
class ProductSubgroupAdmin(admin.ModelAdmin):
    list_display = ("nome", "group", "ativo")
    list_filter = ("group",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("nome", "subgroup", "ativo")
    list_filter = ("subgroup__group",)


@admin.register(ExternalProductMapping)
class ExternalProductMappingAdmin(admin.ModelAdmin):
    list_display = ("external_code", "group", "subgroup")
