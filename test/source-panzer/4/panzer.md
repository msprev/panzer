---
title  : "test"
author : Mark Sprevak
date   : 28 September 2014

style  : MetadataLocal

styledef:
    MetadataLocal:
        all:
            metadata:
                test_bool: true
                test_inline: "test: string"
                test_markdown: "*hello* _world_"
                test_number: 3
                test_list:
                    - item1
                    - item2
                    - item3
                test_list2: [item1, item2, item3]
                test_map:
                    test_inside_map: true
                test_verb: |
                    first paragraph

                    second paragraph
...

