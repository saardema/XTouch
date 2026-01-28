core
	ChannelType(enum):
		Input
		Group
		Aux
		Main

	Control
		value
		parameter: ChannelParameter

	ChannelParameter
		value
		control: Control | None
		channel: MixerChannel

		set_value()
		push_to_mixer()

assignments
	AssignmentManager:
		control_assignments: dict[int, ChannelAssignment]
		mixer_assignments: dict[int, ChannelAssignment]

		assign_mixer_channel()

	ChannelAssignment:
		controller_channel: int
		mixer_channel: MixerChannel | None

mixer
	MixerChannel:
		channel_number: int
		channel_type: ChannelType

		fader: ChannelParameter
		mute: ChannelParameter

	Input(MixerChannel)
		main_mix_send: ChannelParameter
		aux_sends: ChannelParameter[]
		group_sends: ChannelParameter[]

	Group(MixerChannel)
		prefader: ChannelParameter
		aux_sends: ChannelParameter[]

	Aux(MixerChannel)
		prefader: ChannelParameter

	MixerState:
		inputs: Input[]
		groups: Group[]
		aux: Aux[]
		main: MixerChannel

control_surface
	Fader(Control)
	Button(Control)
	Encoder(Control)

	ControlSurface
		midi_adapter: XTouchMidiAdapter

		faderMoved():
		encoderMoved():
		encoderPressed():
		buttonPressed():
			# find parameter
			# notify core

		updateHardwareControl():
			Make midi_adapter push a control's new value/state

motu
	MotuHttpApiClient
		pull()
		pushParameter(param: ChannelParameter)

xtouch
	XTouchMidiAdapter
		# Handles MIDI I/O
		# Abstracts CC/Note as hardware control instance

		cc_lut: cc to fader/encoder mapping
		note_lut: cc to button/encoder mapping
		faders_cc: fader to cc mapping
		encoders_cc: encoder to cc mapping
		encoders_note: encoder to note mapping
		buttons_note: button to note mapping

		on_midi_received()
			translate CC/Note to control instance
			notify controller
		send_note()
		send_cc()