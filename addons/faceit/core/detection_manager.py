import numpy as np

'''
----------------------------------------------------------
Detection Manager for target shapes names.
Can detect slightly different names by levenshtein ratio. 
----------------------------------------------------------
'''


def get_expression_name_double_entries(expression_name, expression_list):
    '''ADD trailing number to double entries! Return the name with .001,.002,.. suffix if multiple entries already exist.'''
    expression_name_final = expression_name

    if expression_name_final in expression_list:
        max_integer_found = 0
        for item_name in [item.name for item in expression_list if expression_name_final in item.name]:
            if len(item_name) >= 3:
                if item_name[-3:].isdigit():
                    if item_name[:-4] == expression_name_final:
                        digits = int(item_name[-3:])
                        max_integer_found = max(max_integer_found, digits)

        if max_integer_found > 0:
            new_digits = '.' + str(max_integer_found + 1).zfill(3)
        else:
            new_digits = '.001'

        expression_name_final += new_digits

    return expression_name_final


def detect_shape(shape_keys, shape_name, min_levenshtein_ratio=1.0, remove_prefix='', remove_suffix=''):
    '''Tries to find the matching shape key by comparing the strings in standardized form
    @shape_keys: the shapekey data that holds the actual blendshapes
    @shape_name: the name of the ARKit expression
    @min_levenshtein_ratio: the ration can be used for fuzzy comparison.
    '''

    found_shape_key_name = ''

    for sk_name in shape_keys:

        st_sk_name = _standardize_shape_name(sk_name)
        st_shape_name = _standardize_shape_name(shape_name)

        if st_sk_name == st_shape_name:
            found_shape_key_name = sk_name
            break
        else:

            # use left and right in full word, because otherwise they will get fuzzy
            levenshtein_ratio = _levenshtein_ratio_and_distance(
                st_sk_name.replace('_l', 'left').replace('_r', 'right'),
                st_shape_name.replace('_l', 'left').replace('_r', 'right'),
                ratio_calc=True)
            if levenshtein_ratio > min_levenshtein_ratio:
                found_shape_key_name = sk_name
                break

    return found_shape_key_name


def _standardize_shape_name(name):
    # List of chars to replace if they are at the start of a shape name
    starts_with = [
        ('_', ''),
        ('Char', ''),
        ('char', '')
    ]

    # Standardize names
    # Make all the underscores!
    name = name.replace(' ', '_') \
        .replace('-', '_') \
        .replace('.', '_') \
        .replace('____', '_') \
        .replace('___', '_') \
        .replace('__', '_') \
        .replace('Right', '_R')\
        .replace('Left', '_L')

    # Replace if name starts with specified chars
    for replacement in starts_with:
        if name.startswith(replacement[0]):
            name = replacement[1] + name[len(replacement[0]):]

    # Remove digits from the start
    name_split = name.split('_')
    if len(name_split) > 1 and name_split[0].isdigit():
        name = name_split[1]

    # Specific condition
    name_split = name.split('"')
    if len(name_split) > 3:
        name = name_split[1]

    # Another specific condition
    if ':' in name:
        for i, split in enumerate(name.split(':')):
            if i == 0:
                name = ''
            else:
                name += split

    # Remove S0 from the end
    if name[-2:] == 'S0':
        name = name[: -2]

    return name.lower()


def _levenshtein_ratio_and_distance(s, t, ratio_calc=True):
    ''' Calculates levenshtein distance between two strings.
        @s: string one
        @t: string two
        @ratio_calc: the function computes the
        levenshtein distance ratio of similarity between two strings
        For all i and j, distance[i,j] will contain the Levenshtein
        distance between the first i characters of s and the
        first j characters of t
    '''
    # Initialize matrix of zeros
    rows = len(s) + 1
    cols = len(t) + 1
    distance = np.zeros((rows, cols), dtype=int)

    # Populate matrix of zeros with the indeces of each character of both strings
    for i in range(1, rows):
        for k in range(1, cols):
            distance[i][0] = i
            distance[0][k] = k

    # Iterate over the matrix to compute the cost of deletions,insertions and/or substitutions
    for col in range(1, cols):
        for row in range(1, rows):
            if s[row - 1] == t[col - 1]:
                # If the characters are the same in the two strings in a given position [i,j] then the cost is 0
                cost = 0
            else:
                # In order to align the results with those of the Python Levenshtein package, if we choose to calculate the ratio
                # the cost of a substitution is 2. If we calculate just distance, then the cost of a substitution is 1.
                if ratio_calc is True:
                    cost = 2
                else:
                    cost = 1
            distance[row][col] = min(distance[row - 1][col] + 1,      # Cost of deletions
                                     distance[row][col - 1] + 1,          # Cost of insertions
                                     distance[row - 1][col - 1] + cost)     # Cost of substitutions
    if ratio_calc is True:
        # Computation of the Levenshtein Distance Ratio
        Ratio = ((len(s) + len(t)) - distance[row][col]) / (len(s) + len(t))
        return Ratio
