from autogen import GroupChat
import inspect

print(f"GroupChat init args: {inspect.signature(GroupChat.__init__)}")
if hasattr(GroupChat, 'auto_select_speaker'):
    print("Has auto_select_speaker")
else:
    print("No auto_select_speaker")