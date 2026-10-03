#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "arx_r5_src/interfaces/InterfacesThread.hpp"
namespace py=pybind11;
PYBIND11_MODULE(r5_live_sdk,m){
 using Arm=arx::r5::InterfacesThread;
 py::class_<Arm>(m,"InterfacesPy")
  .def(py::init<const std::string&,const std::string&,int>(),py::call_guard<py::gil_scoped_release>())
  .def("set_joint_positions",&Arm::setJointPositions)
  .def("set_catch",&Arm::setCatch)
  .def("set_arm_status",&Arm::setArmStatus)
  .def("get_joint_positions",&Arm::getJointPositons)
  .def("get_joint_velocities",&Arm::getJointVelocities)
  .def("get_joint_currents",&Arm::getJointCurrent)
  .def("get_error_codes",&Arm::getErrorCode)
  .def("arx_x",&Arm::arx_x);
}
