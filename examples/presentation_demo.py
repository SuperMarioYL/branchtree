"""Fork a local story, find an explicit contradiction, merge and render."""
import json
from pathlib import Path
import tempfile
from branchtree.tree import StoryTree, Lock
from branchtree.consistency import check_consistency
from branchtree.render_html import render_to_file

tree=StoryTree(name='story-demo')
tree.add_lock(Lock(kind='character',target='林晚',pinned_facts=['左手有疤']))
first=tree.add_chapter('林晚醒来，左手有疤。')
tree.add_chapter('林晚继续赶路。')
tree.branch_from(first.id,'alternate')
tree.add_chapter('林晚低头看，左手没有疤。',branch='alternate')
violations=check_consistency(tree)
before={name:branch.active_tip for name,branch in tree.branches.items()}
tree.merge_branch('alternate')
with tempfile.TemporaryDirectory(prefix='branchtree-demo-') as directory:
    saved=tree.save(directory)
    restored=StoryTree.load(saved)
    html=render_to_file(restored,output=Path(directory)/'tree.html',open_browser=False)
    result={'before_merge':before,'after_merge':{name:branch.active_tip for name,branch in restored.branches.items()},
            'retained_nodes':list(restored.nodes),'violations':[v.model_dump() for v in violations],
            'valid_tree':restored.validate(),'html_written':html.is_file()}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    assert result['valid_tree'] and result['html_written'] and len(violations)==1
