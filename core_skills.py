import random
rand_list = [random.randint(1, 20) for _ in range(10)]

list_comprehension_below_10 = [num for num in rand_list if num < 10]

def less_than_10(num):
    return num < 10
list_comprehension_below_10 = filter(less_than_10, rand_list)