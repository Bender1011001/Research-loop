from pyaedt import Maxwell3d, Desktop
import os

# Geometry: box (ID: N/A)
m3d.modeler.create_box(position=['0', '0', '0'], dimensions_list=['10', '10', '10'], name='Core', matname='iron')

# Setup: transient
setup = m3d.create_setup(setupname='TransientSetup')
setup.props['StopTime'] = '10ms'
setup.props['TimeStep'] = '0.1ms'
setup.props['SaveFields'] = True
setup.update()
