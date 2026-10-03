#!/usr/bin/env python3
"""Offline evidence: pin the SDK binary, inspect joint bounds, count URDF joints."""
import hashlib,json,math,struct,xml.etree.ElementTree as ET
from pathlib import Path
root=Path(__file__).resolve().parents[1]
lib=root/'vendor/R5-master/py/ARX_R5_python/bimanual/api/arx_r5_src/libarx_r5_src.so'
b=lib.read_bytes();digest=hashlib.sha256(b).hexdigest()
expected='30239795532e0d440842405f02092c85f95b5f4b0813c2bdf95b22d89960fa18'
if digest!=expected:raise SystemExit('SDK binary changed; old disassembly offsets cannot be trusted. Re-audit required.')
def double(offset):return struct.unpack_from('<d',b,offset)[0]
low=[double(x) for x in [0x1c0318,0x1c0320,0x1c0320,0x1c0328,0x1c0330,0x1c0338]]
high=[double(x) for x in [0x1c0340,0x1c0348,0x1c0350,0x1c0358,0x1c0360,0x1c0368]]
model=root/'vendor/R5-master/py/ARX_R5_python/bimanual/script/X5liteaa0.urdf'
joints=[{'name':j.attrib['name'],'axis':j.find('axis').attrib['xyz']} for j in ET.parse(model).getroot().findall('joint') if j.attrib['type']=='revolute']
result={'sha256':digest,'arm_dof':len(joints),'gripper_dof':1,'joints':joints,'lower_rad':low,'upper_rad':high,'lower_deg':list(map(math.degrees,low)),'upper_deg':list(map(math.degrees,high)),
 'evidence':{'bounds_initialization':'ControllerBase constructor stores offsets 0x408..0x430 / 0x440..0x468','bounds_usage':'statePositionControl 0x154ad6..0x154b3a clamps first six joints','joint_command':'ControllerThread::setJointPositions 0x161794 loops indices 0..5','gripper_command':'ControllerThread::setCatch 0x161654 writes command index 6','feedback':'ControllerThread::getJointPositons 0x16103e returns 7 values (position minus initialization offset), no division by 5'},
 'follower_type':0,'hardware_validation':False,'gripper_width_mm_from_manual':[0,80],
 'warnings':['URDF limits +/-10 rad are placeholders, not this controller\'s limits.','Master-to-follower gain 5 is not a same-gripper feedback conversion.','Clamp bounds are software evidence, not validation of the user\'s physical model.']}
print(json.dumps(result,indent=2,ensure_ascii=False))
