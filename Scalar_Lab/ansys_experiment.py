from pyaedt import Maxwell3d, Desktop
import os

# Launch Ansys Headless
d = Desktop(specified_version='2024.1', non_graphical=True, new_desktop_session=True, close_on_exit=True)
m3d = Maxwell3d(projectname='SaturationTest', designname='MaxwellDesign1', solution_type='Transient', new_design=True)
m3d.modeler.model_units = 'mm'

# geometry_shapes: box (ID: N/A)
m3d.modeler.create_box(position=['0', '0', '0'], dimensions_list=['10', '10', '10'], name='Core', matname='iron')

# setup: transient
setup = m3d.create_setup(setupname='TransientSetup')
setup.props['StopTime'] = '10ms'
setup.props['TimeStep'] = '0.1ms'
setup.props['SaveFields'] = True
setup.update()

# analyze: run
m3d.analyze_setup('TransientSetup')
