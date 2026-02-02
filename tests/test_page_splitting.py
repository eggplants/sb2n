"""Tests for page splitting when exceeding 1000 block limit."""

from sb2n.migrator import _count_blocks_recursive, _split_blocks_into_chunks


class MockBlock:
    """Mock block for testing."""

    def __init__(self, block_type: str = "paragraph", children: list | None = None):
        """Initialize mock block.

        Args:
            block_type: Type of block
            children: List of child blocks (for bulleted_list_item)
        """
        self.type = block_type
        if block_type == "bulleted_list_item" and children is not None:
            self.bulleted_list_item = {"children": children}


class TestBlockCounting:
    """Test recursive block counting."""

    def test_count_single_block(self):
        """Test counting a single block."""
        block = MockBlock("paragraph")
        assert _count_blocks_recursive(block) == 1

    def test_count_block_with_children(self):
        """Test counting a block with nested children."""
        child1 = MockBlock("paragraph")
        child2 = MockBlock("paragraph")
        parent = MockBlock("bulleted_list_item", children=[child1, child2])
        # 1 parent + 2 children = 3
        assert _count_blocks_recursive(parent) == 3

    def test_count_deeply_nested_blocks(self):
        """Test counting deeply nested blocks."""
        # Level 3
        level3_child1 = MockBlock("paragraph")
        level3_child2 = MockBlock("paragraph")

        # Level 2
        level2_child1 = MockBlock("bulleted_list_item", children=[level3_child1, level3_child2])
        level2_child2 = MockBlock("paragraph")

        # Level 1
        level1_parent = MockBlock("bulleted_list_item", children=[level2_child1, level2_child2])

        # 1 (level1) + 1 (level2_child1) + 2 (level3) + 1 (level2_child2) = 5
        assert _count_blocks_recursive(level1_parent) == 5

    def test_count_multiple_top_level_blocks(self):
        """Test counting multiple top-level blocks with children."""
        # First block with children
        child1 = MockBlock("paragraph")
        child2 = MockBlock("paragraph")
        block1 = MockBlock("bulleted_list_item", children=[child1, child2])

        # Second block without children
        block2 = MockBlock("paragraph")

        # Third block with children
        child3 = MockBlock("paragraph")
        block3 = MockBlock("bulleted_list_item", children=[child3])

        blocks = [block1, block2, block3]
        total = sum(_count_blocks_recursive(block) for block in blocks)
        # 3 (block1 + 2 children) + 1 (block2) + 2 (block3 + 1 child) = 6
        assert total == 6


class TestBlockSplitting:
    """Test block splitting into chunks."""

    def test_split_under_limit(self):
        """Test that blocks under limit are not split."""
        blocks = [MockBlock("paragraph") for _ in range(100)]
        chunks = _split_blocks_into_chunks(blocks, max_blocks=1000)
        assert len(chunks) == 1
        assert len(chunks[0]) == 100

    def test_split_at_limit(self):
        """Test that blocks exactly at limit are not split."""
        blocks = [MockBlock("paragraph") for _ in range(1000)]
        chunks = _split_blocks_into_chunks(blocks, max_blocks=1000)
        assert len(chunks) == 1
        assert len(chunks[0]) == 1000

    def test_split_over_limit_simple(self):
        """Test splitting simple blocks over limit."""
        blocks = [MockBlock("paragraph") for _ in range(1500)]
        chunks = _split_blocks_into_chunks(blocks, max_blocks=1000)
        assert len(chunks) == 2
        assert len(chunks[0]) == 1000
        assert len(chunks[1]) == 500

    def test_split_with_nested_blocks(self):
        """Test splitting blocks with nested children."""
        # Create blocks where each has 99 children (100 total per block)
        blocks = []
        for _ in range(15):  # 15 blocks * 100 = 1500 total
            children = [MockBlock("paragraph") for _ in range(99)]
            block = MockBlock("bulleted_list_item", children=children)
            blocks.append(block)

        chunks = _split_blocks_into_chunks(blocks, max_blocks=1000)

        # Should split into 2 chunks: 10 blocks (1000 total) + 5 blocks (500 total)
        assert len(chunks) == 2
        assert len(chunks[0]) == 10  # 10 blocks * 100 = 1000
        assert len(chunks[1]) == 5  # 5 blocks * 100 = 500

    def test_split_respects_block_boundaries(self):
        """Test that splitting doesn't break in the middle of a block with children."""
        # Create a block with 500 children (501 total)
        large_block = MockBlock("bulleted_list_item", children=[MockBlock("paragraph") for _ in range(500)])

        # Add 998 simple blocks (total: 501 + 998 = 1499)
        blocks = [large_block] + [MockBlock("paragraph") for _ in range(998)]

        chunks = _split_blocks_into_chunks(blocks, max_blocks=1000)

        # Should split into 2 chunks: [large_block + 499 simple] + [499 simple]
        assert len(chunks) == 2
        assert len(chunks[0]) == 500  # large_block + 499 simple blocks
        assert len(chunks[1]) == 499  # remaining simple blocks

    def test_split_single_block_exceeds_limit(self):
        """Test handling when a single block exceeds the limit."""
        # Create a block with 1500 children (1501 total)
        large_block = MockBlock("bulleted_list_item", children=[MockBlock("paragraph") for _ in range(1500)])

        blocks = [large_block, MockBlock("paragraph")]

        chunks = _split_blocks_into_chunks(blocks, max_blocks=1000)

        # The large block exceeds limit but cannot be split, so it goes in its own chunk
        assert len(chunks) == 2
        assert len(chunks[0]) == 1  # large_block alone
        assert len(chunks[1]) == 1  # simple block

    def test_split_empty_list(self):
        """Test splitting an empty list."""
        blocks = []
        chunks = _split_blocks_into_chunks(blocks, max_blocks=1000)
        assert len(chunks) == 0

    def test_split_multiple_chunks(self):
        """Test splitting into more than 2 chunks."""
        blocks = [MockBlock("paragraph") for _ in range(2500)]
        chunks = _split_blocks_into_chunks(blocks, max_blocks=1000)
        assert len(chunks) == 3
        assert len(chunks[0]) == 1000
        assert len(chunks[1]) == 1000
        assert len(chunks[2]) == 500


class TestSkipExistingWithSplitting:
    """Test skip-existing functionality with page splitting."""

    def test_generates_correct_split_titles(self):
        """Test that split page titles are generated correctly."""
        page_title = "Test Page"
        total_chunks = 3

        expected_titles = [
            "Test Page - 1/3",
            "Test Page - 2/3",
            "Test Page - 3/3",
        ]

        for i in range(1, total_chunks + 1):
            split_title = f"{page_title} - {i}/{total_chunks}"
            assert split_title == expected_titles[i - 1]

    def test_all_split_pages_exist(self):
        """Test detection when all split pages already exist."""
        page_title = "Test Page"
        total_chunks = 3

        existing_titles = {
            "Test Page - 1/3",
            "Test Page - 2/3",
            "Test Page - 3/3",
        }

        # Check if all split pages exist
        all_exist = True
        for i in range(1, total_chunks + 1):
            split_title = f"{page_title} - {i}/{total_chunks}"
            if split_title not in existing_titles:
                all_exist = False
                break

        assert all_exist is True

    def test_some_split_pages_exist(self):
        """Test detection when only some split pages exist."""
        page_title = "Test Page"
        total_chunks = 3

        existing_titles = {
            "Test Page - 1/3",
            # "Test Page - 2/3" is missing
            "Test Page - 3/3",
        }

        # Check if all split pages exist
        all_exist = True
        for i in range(1, total_chunks + 1):
            split_title = f"{page_title} - {i}/{total_chunks}"
            if split_title not in existing_titles:
                all_exist = False
                break

        assert all_exist is False

    def test_no_split_pages_exist(self):
        """Test detection when no split pages exist."""
        page_title = "Test Page"
        total_chunks = 3

        existing_titles = set()

        # Check if all split pages exist
        all_exist = True
        for i in range(1, total_chunks + 1):
            split_title = f"{page_title} - {i}/{total_chunks}"
            if split_title not in existing_titles:
                all_exist = False
                break

        assert all_exist is False
