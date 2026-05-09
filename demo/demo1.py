from decimal import Decimal, ROUND_HALF_UP

base = Decimal("1")
ratio = Decimal("0.99")
diff = Decimal("1") - ratio

scale = Decimal("0.0001")

count = 15

list_price = []
sum0, sum1, sum2, sum3 = Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0")
for i in range(count):
    base = (base * ratio).quantize(scale, ROUND_HALF_UP)
    sum0 += diff
    sum1 += (diff / base).quantize(scale, ROUND_HALF_UP)
    sum2 += diff * ((Decimal("1") + diff) ** i).quantize(scale, ROUND_HALF_UP)
    sum3 += diff * ((Decimal("1") + diff) ** i / base).quantize(scale, ROUND_HALF_UP)


print(sum0)
print(sum1, (sum1 / sum0).quantize(scale, ROUND_HALF_UP))
print(sum2, (sum2 / sum0).quantize(scale, ROUND_HALF_UP))
print(sum3, (sum3 / sum0).quantize(scale, ROUND_HALF_UP))
