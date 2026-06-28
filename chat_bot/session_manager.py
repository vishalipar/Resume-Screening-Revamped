conversation_states = {}

class ConversationState:
    def __init__(self):
        self.stage = 'idle'
        self.jd_data = {}
        self.last_resume_id = None
        
    def reset(self):
        self.stage = 'idle'
        self.jd_data = {}
        
def get_or_create_state(session_id):
    if session_id not in conversation_states:
        conversation_states[session_id] = ConversationState()
    return conversation_states[session_id]