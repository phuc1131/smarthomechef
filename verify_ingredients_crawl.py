#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from apps.nutrition.models import Ingredient

total = Ingredient.objects.count()
ids = sorted(list(Ingredient.objects.values_list('id', flat=True)))
is_sequential = ids == list(range(1, len(ids)+1))

print(f'Total ingredients: {total}')
print(f'ID range: {min(ids) if ids else 0} - {max(ids) if ids else 0}')
print(f'Sequential 1-N: {is_sequential}')
print(f'\nFirst 10 ingredients:')
for ing in Ingredient.objects.all()[:10]:
    print(f'  {ing.id:4d}. {ing.name}')
print(f'\nLast 10 ingredients:')
for ing in Ingredient.objects.all().order_by('-id')[:10]:
    print(f'  {ing.id:4d}. {ing.name}')
