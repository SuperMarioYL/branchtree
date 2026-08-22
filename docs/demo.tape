Output assets/demo.gif
Set FontSize 16
Set Width 1200
Set Height 720
Set Theme Dracula
Set Padding 20

# Create a fresh workspace for the demo
Type "mkdir -p /tmp/bt-demo && cd /tmp/bt-demo && rm -rf myserial.tree"
Enter
Sleep 1s

# Create a story tree
Type "branchtree new myserial"
Enter
Sleep 1s

# Add chapters
Type 'branchtree add --text "ch1: Lin Wan woke from a nightmare, the old scar on her left hand aching."'
Enter
Sleep 1s

Type 'branchtree add --text "ch2: Lin Wan walked down Zhuque Avenue in Changan."'
Enter
Sleep 1s

Type 'branchtree add --text "ch3: Lin Wan met Zhou Yuan, the only constable who knew the truth."'
Enter
Sleep 1s

# Lock character facts (immutable across regeneration)
Type 'branchtree lock add character:LinWan --facts "left-hand scar;hates her brother"'
Enter
Sleep 1s

# Fork a branch from chapter 3
Type "branchtree branch --from ch3 --name alt-take"
Enter
Sleep 1s

# Write the alternate take
Type 'branchtree add --text "alt: Lin Wan strikes first." --branch alt-take'
Enter
Sleep 1s

# Check cross-chapter consistency
Type "branchtree consistency"
Enter
Sleep 1s

# Render the static HTML tree view
Type "branchtree view --no-browser"
Enter
Sleep 2s

# Merge the best take back to the main line
Type "branchtree merge --branch alt-take --into main"
Enter
Sleep 1s

Type "ls myserial.tree/"
Enter
Sleep 1s
