def traverse_tree(t, exclude_parent=False):
    if not exclude_parent:
        yield t
    for child in t.children:
        if exclude_parent:
            yield child
        yield from traverse_tree(child, exclude_parent)


def traverse_tree_from_iteration(iterator):
    for obj in iterator:
        yield obj
        for child in obj.children:
            yield from traverse_tree(child, exclude_parent=False)


def isclose(a, b, rel_tol=1e-09, abs_tol=0.001):
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def matrix_to_list(matrix):
    return [x for lis in [x[:] for x in [list(y) for y in matrix[:]]] for x in lis]


# used for testing if the bake tool worked
def isclose_matrix(matrix_a, matrix_b, rel_tol=1e-09, abs_tol=0.001):
    floats_a = matrix_to_list(matrix_a)
    floats_b = matrix_to_list(matrix_b)
    for i in range(0, len(floats_a)):
        if not isclose(floats_a[i], floats_b[i], rel_tol=rel_tol, abs_tol=abs_tol):
            return False
    return True
