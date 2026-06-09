def quicksort(arr):
    """
    Sort a list using the quicksort algorithm.

    Parameters:
    arr (list): A list of comparable elements to be sorted.

    Returns:
    list: A new list containing all elements from the input list sorted in ascending order.

    Raises:
    TypeError: If the input is not a list or contains incomparable elements.

    Examples:
    >>> quicksort([])
    []
    >>> quicksort([5])
    [5]
    >>> quicksort([3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5])
    [1, 1, 2, 3, 3, 4, 5, 5, 5, 6, 9]
    >>> quicksort(['banana', 'apple', 'cherry'])
    ['apple', 'banana', 'cherry']
    """
    # Input validation
    if not isinstance(arr, list):
        raise TypeError("Input must be a list")

    # Base case: empty list or single element list is already sorted
    if len(arr) <= 1:
        return arr.copy()

    # Pivot selection: choose the middle element
    pivot_index = len(arr) // 2
    pivot = arr[pivot_index]

    # Partitioning: create left, middle, and right sublists
    left = [x for i, x in enumerate(arr) if x < pivot]
    middle = [x for i, x in enumerate(arr) if x == pivot]
    right = [x for i, x in enumerate(arr) if x > pivot]

    # Recursively sort left and right sublists and combine results
    return quicksort(left) + middle + quicksort(right)