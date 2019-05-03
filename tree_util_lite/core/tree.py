from tree_util_lite.common.util import *

_STOP_TRAVERSAL = 0xffffffffffff


class AddAncestorAsChild(TreeUtilError):
    """Adding ancestor of a node to its children list is forbidden."""


class SetDescendantAsParent(TreeUtilError):
    """Setting descendant of a node as new parent is forbidden."""


class SameNode(TreeUtilError):
    """Name point to the same node."""


class LabelClashing(TreeUtilError):
    """Name clashing when add child Node."""


class Node(object):
    """Represent a node in tree.

    Attributes:
        _label (str):
        _data (dict):
        _parent (Node):
        _children (list of Node): Not exists if Node is file

    Properties:
        label (str):
        path (Path):
        parent (Node):
        children (list of Node):
        ancestor (list of Node):
        descendant (list of Node):
        sibling (list of Node):
        child_count (int):
        depth (int):
        level (int):
        height (int):
        is_leaf (bool):
        is_branch (bool):
        is_root (bool):
        is_isolated (bool):
        data (dict):

    Methods:
        relabel()
        set_parent()
        add_children()
        remove_children()
        add_subpath()
        contain_subpath()
        traverse_preorder()
        traverse_postorder()
        traverse_levelorder()
        render_subtree()
        isolate()
        insert()
        delete()
        cut()

    """

    def __init__(self, label, parent=None, data=None, verbose=0):
        """
        Args:
            label (str):
            parent (Node):
            data (dict): custom data

        """

        super(Node, self).__init__()
        self._label = label
        self._data = data
        self._parent = parent
        self._children = []
        self._verbose = verbose

        self.set_parent(parent)

    @property
    def label(self):
        """str: """
        return self._label

    @property
    def data(self):
        """dict: """
        return self._data

    @property
    def child_count(self):
        """int: also known as the degree of node."""
        return len(self._children)

    @property
    def path(self):
        """Path: """
        cur_parent = self._parent
        parts = [self._label]
        while cur_parent:
            parts.insert(0, cur_parent.label)
            cur_parent = cur_parent.parent
        return Path(*parts)

    @property
    def nice_path(self):
        """str: """
        return self.path.as_posix()

    @property
    def depth(self):
        """int: """
        depth = 0
        cur_parent = self._parent
        while cur_parent:
            depth += 1
            cur_parent = cur_parent._parent
        return depth

    @property
    def level(self):
        """int: """
        level = 1
        cur_parent = self._parent
        while cur_parent:
            level += 1
            cur_parent = cur_parent._parent
        return level

    @property
    def height(self):
        """int: """
        def depth(node):
            return node.depth, 0

        return self.traverse_levelorder(depth)[-1] - self.depth

    @property
    def is_leaf(self):
        """bool: """
        return 0 if self.children else 1

    @property
    def is_branch(self):
        """bool: """
        return 1 if self.children else 0

    @property
    def is_root(self):
        """bool: """
        return 1 if not self._parent else 0

    @property
    def is_isolated(self):
        """bool: """
        return not self.parent and not self.children

    @property
    def parent(self):
        """Node: """
        return self._parent

    @property
    def children(self):
        """list of Node: """
        return self._children

    @property
    def ancestor(self):
        """list of Node: """
        ret = []
        cur_parent = self.parent
        while cur_parent:
            ret.append(cur_parent)
            cur_parent = cur_parent.parent
        return ret

    @property
    def descendant(self):
        """list of Node: """
        return self.traverse_levelorder()[1:]

    @property
    def sibling(self):
        """list of Node: """
        return [n for n in self._parent.children if n is not self]

    def _validate_node(self, node):
        """Make sure `node` is valid for `self` to operate on.

        Raises:
            SameNode:
            InvalidType:
        Returns:
            bool:
        """

        if node is None:
            return 0
        if node is self:
            raise SameNode('"{}" is the same as "{}"'.format(node.nice_path, self.nice_path))
        check_type(node, [Node])
        return 1

    def _validate_child(self, node):
        """Check if a node is qualified to be added as child of `self`.

        Statisfy condition
            `node.label` do not clash among nodes in `self.children`.
            `node` does not belong to `self.ancestor`

        Args:
            node (Node):

        Raises:
            LabelClashing:
            InvalidType:
            AddAncestorAsChild:

        Returns:
            bool:
        """

        check_type(node, [Node])

        for n in self.children:
            if n.label == node.label and n is not node:
                msg = 'There is already a child with label "{}" under "{}"'.format(n.label, self.nice_path)
                raise LabelClashing(msg)
        if node in self.ancestor:
            msg = '"{}" is ancestor of "{}"'.format(node.nice_path, self.nice_path)
            raise AddAncestorAsChild(msg)
        return 1

    def _validate_parent(self, node):
        """Check if a node is qualified to be set as parent of `self`.

        Statisfy condition
            `self.label` do not clash among nodes in `node.children`.
            `node` does not belong to `self.descendant`

        Args:
            node (Node):

        Raises:
            LabelClashing:
            InvalidType:
            SetDescendantAsParent:

        Returns:
            bool:
        """

        check_type(node, [Node])

        for n in node.children:
            if n.label == self.label and n is not self:
                msg = 'There is already a child with label "{}" under "{}"'.format(self.label, node.nice_path)
                raise LabelClashing(msg)
        if node in self.descendant:
            msg = '"{}" is descendant of "{}"'.format(node.nice_path, self.nice_path)
            raise SetDescendantAsParent(msg)
        return 1

    def relabel(self, label):
        """Relabel node after checking for label clashing.

        Args:
            label (str):
        """

        sibling_labels = [n.label for n in self.sibling]
        if label in sibling_labels:
            raise LabelClashing('There is already a sibling with label "{}"'.format(label))
        self._label = label

    def set_parent(self, parent):
        """
        Args:
            parent (Node):
        """

        if parent is None:
            self._parent = None

        if not self._validate_node(parent):
            return 0

        if not self._validate_parent(parent):
            return 0

        # Remove `self` as child from current parent of `self`
        if self._parent != parent and self._parent:
            cur_parent = self._parent
            if self in cur_parent.children:
                cur_parent.children.remove(self)

        self._parent = parent

        if self._verbose:
            log_info('"{}" set "{}" as parent'.format(
                self.nice_path,
                parent.nice_path
            ))

        if self not in parent.children:
            parent.add_children(self)
        return 1

    def add_children(self, *args):
        """Add multiple nodes as children.

        Args:
            args (list): mixed list of [str, Node]
        """

        ret = []
        children = [Node(a) for a in args if check_type(a, [str], raise_exception=0) and a]
        children.extend([a for a in args if check_type(a, [Node], raise_exception=0)])
        for child in children:
            if not self._validate_node(child):
                continue

            if not self._validate_child(child):
                continue

            for n in self._children:
                if n.label == child.label:
                    continue
            self._children.append(child)

            if self._verbose:
                log_info('"{}" added "{}" as child'.format(
                    self.nice_path,
                    child.nice_path
                ))

            if child.parent != self:
                child.set_parent(self)
            ret.append(child)
        return ret

    def remove_children(self, *args):
        """Remove multiple child nodes from `self`.

        Subtrees of children are kept intact.

        Args:
            args (list): mixed list of [str, Node]
        """

        children_labels = [a for a in args if check_type(a, [str], raise_exception=0) and a]
        for n in self._children:
            if n.label in children_labels:
                self._children.remove(n)

        children = [a for a in args if check_type(a, [Node], raise_exception=0) and a]
        for n in self._children:
            if n in children:
                self._children.remove(n)

    def add_subpath(self, *args):
        """
        Args:
            args (list): mixed list of [str, Path, Node]
        """

        def to_part(a):
            if check_type(a, [str, PurePath], raise_exception=0):
                return str(a)
            elif check_type(a, [Node], raise_exception=0):
                return a.label
            else:
                return ''

        ret = []
        subpath = Path('/'.join([to_part(a) for a in args]))
        cur_node = self
        for label in subpath.parts:
            exists = 0
            for c in cur_node.children:
                if label == c.label:
                    cur_node = c
                    ret.append(cur_node)
                    exists = 1
                    break
            if not exists:
                cur_node = Node(label, parent=cur_node)
                ret.append(cur_node)
        return ret

    def contain_subpath(self, subpath):
        """Check if `subpath` is under `self` node.

        Args:
            subpath (str or Path): path of sub tree to be appended under `self`
        """

        subpath = Path(subpath)
        cur_node = self
        for label in subpath.parts:
            found = 0
            for c in cur_node.children:
                if c.label == label:
                    cur_node = c
                    found = 1
                    break
            if not found:
                return 0
        return 1

    def traverse_preorder(self, func=None):
        """Depth-first search.

        Args:
            func: function with node visit logic
                Must return 2-tuple:
                    (
                        visited: arbitrary value,
                        bool: stop traversal flag
                    )
                By default, return (node, 0)

        Returns:
            list: list of visited node, the last one is "the one" node stop the traversal
        """

        def default_func(node):
            return node, 0

        if self._verbose:
            log_info('Start pre-order traversal on "{}"..'.format(self.nice_path))

        if not func:
            func = default_func

        def _preorder(node, func):
            discovered = []

            # Visit `node`
            visited, stop = func(node)
            discovered.append(visited)
            if stop:
                discovered.append(_STOP_TRAVERSAL)

            # Visit sub trees of `node`
            for n in node.children:

                # Stop traversal condition
                if discovered[-1] == _STOP_TRAVERSAL:
                    return discovered

                discovered.extend(_preorder(n, func))
            return discovered

        ret = _preorder(self, func)
        return ret if ret[-1] != _STOP_TRAVERSAL else ret[:-1]

    def traverse_postorder(self, func=None):
        """Depth-first search.

        Args:
            func: function with node visit logic
                Must return 2-tuple:
                    (
                        visited: arbitrary value,
                        bool: stop traversal flag
                    )
                Default:
                    lambda node: (node, 0)
        Returns:
            list: list of visited node, the last one is "the one" node stop the traversal
        """

        def default_func(node):
            return node, 0

        if self._verbose:
            log_info('Start post-order traversal on "{}"..'.format(self.nice_path))

        if not func:
            func = default_func

        def _postorder(node, func):
            discovered = []

            # Visit sub trees of `node`
            for n in node.children:
                subret = _postorder(n, func)
                discovered.extend(subret)

                # Stop traversal condition
                if subret[-1] == _STOP_TRAVERSAL:
                    return discovered

            # Visit `node`
            visited, stop = func(node)
            discovered.append(visited)
            if stop:
                discovered.append(_STOP_TRAVERSAL)
            return discovered

        ret = _postorder(self, func)
        return ret if ret[-1] != _STOP_TRAVERSAL else ret[:-1]

    def traverse_levelorder(self, func=None):
        """Breadth-first search.

        Args:
            func: function with node visit logic
                Must return 2-tuple:
                    (
                        visited: arbitrary value,
                        bool: stop traversal flag
                    )
                Default:
                    lambda node: (node, 0)
        Returns:
            list: list of visited node, the last one is "the one" node stop the traversal
        """

        def default_func(node):
            return node, 0

        if self._verbose:
            log_info('Start level-order traversal on "{}"..'.format(self.nice_path))

        if not func:
            func = default_func

        discovered = []
        queue = [self]
        while queue:
            node = queue.pop()

            # Visit `node`
            visited, stop = func(node)
            discovered.append(visited)

            # Stop traversal condition
            if stop:
                return discovered

            for n in node.children:
                queue.insert(0, n)

        return discovered

    def render_subtree(self):
        """Print tree hierarchy in console."""

        cur_root_depth = self.depth

        def print_indent(node):
            print('|---' * (node.depth - cur_root_depth) + node.label)
            return 0, 0

        self.traverse_preorder(print_indent)

    def isolate(self):
        """Isolate `self` from its connected nodes if any.

        Steps:
            Remove `self` from `self.parent.children`
            Set `self.parent` to None
            Set parent of all items in `self.children` to None
            Make `self.children` empty
        """

        if self.parent:
            if self in self.parent.children:
                self.parent.children.remove(self)
        self.set_parent(None)
        for n in self._children:
            n.set_parent(None)
        self._children = []

    def insert(self, node, below=0):
        """Insert a new node at position right above `self`, make it new parent of `self`.

        `node` will be isolated from its tree ( if any ) before inserted.

        Args:
            node (str or Node): node to be inserted
                A new node will be created if a label is provided
            below (bool): insert below `self` instead
                All children of `self` will be re-parented to new node
        Raises:
            InvalidType:
        Returns:
            Node:
        """

        if check_type(node, [Node], raise_exception=0):
            node.isolate()
        elif check_type(node, [str], raise_exception=0):
            node = Node(node)

        cur_parent = self.parent
        self.set_parent(node)
        node.set_parent(cur_parent)

        return node

    def delete(self):
        """Delete `self` from linked nodes chain ( tree ),
        `self.children` will be re-parented to `self.parent`.
        """

        cur_parent = self.parent
        cur_children = self.children
        self.isolate()
        cur_parent.add_children(*cur_children)

    def cut(self):
        """Disconnect `self` from its parent."""

        if self in self.parent.children:
            self.parent.children.remove(self)
        self.set_parent(None)

    def lowest_common_ancestor(self, node):
        """Find lowest common ancestor of `self` and `node`.

        Args:
            node (Node):
        Returns:
            Node:
        """

        check_type(node, [Node])

        self_ancestor = self.ancestor
        self_ancestor_size = len(self_ancestor)
        node_ancestor = node.ancestor
        node_ancestor_size = len(node_ancestor)

        if self_ancestor_size >= node_ancestor_size:
            max_len = self_ancestor_size
            node_ancestor = [None] * (self_ancestor_size - node_ancestor_size) + node_ancestor
        else:
            max_len = node_ancestor_size
            self_ancestor = [None] * (node_ancestor_size - self_ancestor_size) + self_ancestor

        for i in range(max_len):
            if self_ancestor[i] is node_ancestor[i]:
                return self_ancestor[i]


class Tree(object):
    """A generic ordered-tree of Node objects.

    Attributes:
        _tree_name (str):
        _root (Node):

    Properties:
        tree_name (str):
        root (Node):

    Methods:
        ls()
        search()
        insert()
        delete()
        lowest_common_ancestor()

    """

    def __init__(self, tree_name, root_name, verbose=0):
        """
        Args:
            tree_name (str):
            root_name (str):
        """

        super(Tree, self).__init__()
        self._tree_name = tree_name
        self._root = Node(
            '{}_root'.format(tree_name) if not root_name else root_name,
            verbose=verbose
        )

    @property
    def tree_name(self):
        """str: """
        return self._tree_name

    @property
    def root(self):
        """Node: auto update new root."""
        root = self._root if not self._root.parent else self._root.ancestor[-1]
        return root

    def ls(self, node=None, pattern=None, return_label=0):
        """List nodes in tree using level-order traversal.

        List all nodes by default.

        Args:
            node (Node): list descendant of `node`
                None for listing all nodes in tree
            pattern (str): glob pattern
                If relative, the path can be either relative or absolute,
                and matching is done from the right
                Example:
                    'a/b.py' match '*.py'
                    '/a/b/c.py' match '/a/*/*.py'
                    '/a/b/c.py' does not match 'a/*.py'
                If absolute, the path must be absolute, and the whole path must match
                Example:
                    '/a.py' match '/*.py'
                    'a/b.py' does not match '/*.py'
            return_label (bool): return list of node labels

        Raises:
            InvalidType:

        Returns:
            list of Node:
        """

        check_type(node, [Node, type(None)])
        check_type(pattern, [str, type(None)])

        listed_nodes = node.descendant if node else [self.root] + self.root.descendant
        if pattern:
            listed_nodes = [n for n in listed_nodes if n.path.match(pattern)]

        return [n.label if return_label else n for n in listed_nodes]

    def search(self, pattern, return_label=0):
        """Search for nodes in tree, start from `self.root`.

        Args:
            pattern (str): glob pattern for searching all descendant of `self.root`
                Same rule as `pattern` argument in `self.ls()`

        Returns:
            list of Node:
        """

        return self.ls(pattern=pattern, return_label=return_label)

    def insert(self, node, target):
        """Insert `node` into `target`, making `node` the new parent of `target`

        Wrap `Node.insert()`

        Args:
            node (Node):
            targe (Node):

        Raises:
            InvalidType:

        Returns:
            Node:
        """

        check_type(node, [Node])
        check_type(target, [Node])

        return target.insert(node)

    def delete(self, node):
        """Wrap `Node.delete()`

        Args:
            node (Node):

        Raises:
            InvalidType:
        """

        check_type(node, [Node])

        node.delete()

    def lowest_common_ancestor(self, node1, node2):
        """Wrap `Node.lowest_common_ancestor()`

        Raises:
            InvalidType:

        Returns:
            Node:
        """

        check_type(node1, [Node])
        check_type(node2, [Node])

        return node1.lowest_common_ancestor(node2)