import ctypes.util
from ctypes import *
import time
import sys
from .utils import pollHelper
#if type error make "str" as b"str"
nip2pErrors = {
    0: "P2PStatusSuccess",
    # Errors
    -308000:   "P2PStatusMemoryFull",
    -308001:   "P2PStatusNotSupported",
    -308002:   "P2PStatusIOOperationFailed",
    -308003:   "P2PStatusDeviceNotFound",
    -308004:   "P2PStatusBadPointer",
    -308005:   "P2PStatusStreamResourcesInUse",
    -308006:   "P2PStatusEndpointAlreadyExists",
    -308007:   "P2PStatusEndpointNotFound",
    -308008:   "P2PStatusEndpointsAreEquivalent",
    -308009:   "P2PStatusInvalidStreamId",
    -308010:   "P2PStatusDeviceAlreadyExists",
    -308011:   "P2PStatusStreamNotFound",
    -308012:   "P2PStatusStreamNotLinked",
    -308013:   "P2PStatusInvalidEndpointInterface",
    -308014:   "P2PStatusEndpointNotCapable",
    -308015:   "P2PStatusStreamNotEnabled",
    -308016:   "P2PStatusInvalidStreamHandle",
    -308017:   "P2PStatusInvalidAttributeType",
    -308018:   "P2PStatusInvalidAttribute",
    -308019:   "P2PStatusIncompatibleEndpoints",
    -308020:   "P2PStatusPeerInterfaceNotSupported",
    -308021:   "P2PStatusInvalidEndpointHandle",
    -308022:   "P2PStatusIncompatibleDataTypes",
    -308023:   "P2PStatusInvalidEvent",
    -308024:   "P2PStatusOperationTimedOut",
    -308025:   "P2PStatusStreamWasClosed",
    -308026:   "P2PStatusAttributeNotSettable",
    -308027:   "P2PStatusEndpointsOnSameDevice",
    -308028:   "P2PStatusEventNotSupported",
    -308029:   "P2PStatusEventUnregistered",
    -308030:   "P2PStatusInvalidP2PLinkPath",
    -308031:   "P2PStatusSoftwareFault",
    -308032:   "P2PStatusInvalidDataType",
    # Warnings
    308000:    "P2PStatusDataTypeSignMismatch"
    }

# Create constants for error codes
for code, name in list(nip2pErrors.items()):
    globals()[name] = code

nip2pStates = { 0: { 'name': 'kStreamStateUnlinked'     , 'short_name': 'Unlinked'      },
                     1: { 'name': 'kStreamStateDisabled'     , 'short_name': 'Disabled'      },
                     2: { 'name': 'kStreamStateEnabled'      , 'short_name': 'Enabled'       },
                     3: { 'name': 'kStreamStateFlushing'     , 'short_name': 'Flushing'      },
                     4: { 'name': 'kStreamStatePaused'       , 'short_name': 'Paused'        },
                     5: { 'name': 'kStreamStateLinkValidated', 'short_name': 'LinkValidated' } }

# Create constants for states codes
for id, stateDict in list(nip2pStates.items()):
    globals()[stateDict['name']] = id

nip2pAttributes = { 0: 'kStreamAttributeStreamState',
                          # Writer specific
                          0x10000000: 'kStreamAttributeWriterNumElementsForWriting',
                          0x10000001: 'kStreamAttributeWriterSizeInElements',
                          0x10000002: 'kStreamAttributeWriterOverflow',
                          # Reader specific
                          0x20000000: 'kStreamAttributeReaderNumElementsForReading',
                          0x20000001: 'kStreamAttributeReaderSizeInElements',
                          0x20000002: 'kStreamAttributeReaderUnderflow' }

# Create constants for attribute codes
for id, attributename in list(nip2pAttributes.items()):
    globals()[attributename] = id

class P2PStateException(Exception):
    def __init__(self, expectedState, actualState):
        self.expectedState = expectedState
        self.actualState   = actualState
    def __str__(self):
        return 'Expected state ' + p2pStateToStr(self.expectedState) + ', but state is actually ' + p2pStateToStr(self.actualState)

def p2pStateToStr(state):
    if state in nip2pStates:
        return nip2pStates[state]['short_name']
    else:
        return '(unknown state ' + str(state) + ')'

def p2pErrorToStr(code):
    if code in nip2pErrors:
        return nip2pErrors[code]
    else:
        return '(unknown code ' + str(code) + ')'

class P2PException(Exception):
    def __init__(self, errorCode):
        self.errorCode = errorCode
    def __str__(self):
        if self.errorCode in nip2pErrors:
            return nip2pErrors[self.errorCode] + '(' + str(self.errorCode) + ')'
        else:
            return "Unknown error returned from p2p function " + str(self.errorCode)

def assertP2PSuccess(p2pstatus):
    if p2pstatus != 0:
        raise P2PException(p2pstatus)

def expectP2PError(expectedError):
    return AssertP2PError(P2PException(expectedError))

class AssertP2PError(object):
     def __init__(self, exception):
          self.exception = exception

     def __enter__(self):
          pass

     def __exit__(self, err_type, err_value, err_traceback):
          if not err_type:
                raise AssertionError('Expected error: %s, but no error thrown' % (self.exception))
          elif err_type != type(self.exception):
                raise AssertionError('Expected error: %s, but got error: %s' % (self.exception, err_type))
          elif err_value.errorCode != self.exception.errorCode:
                raise AssertionError('Expected P2PException: %s, but got exception: %s' % (self.exception, err_value))
          return True

class NIP2PLibrary:
    def __init__(self):
        self.p2pdll = ctypes.cdll.LoadLibrary(ctypes.util.find_library('nip2p'))

        self.nip2pCreateAndLinkStream = self.p2pdll.nip2pCreateAndLinkStream
        self.nip2pCreateAndLinkStream.argtypes = [c_uint, c_uint, c_ubyte, POINTER(c_uint)]

        self.nip2pFlushAndDisableStream = self.p2pdll.nip2pFlushAndDisableStream
        self.nip2pFlushAndDisableStream.argtypes = [c_uint, c_int, POINTER(c_bool)]

        # The following functions are simple enough that we don't need to explicitly call out the prototypes
        self.nip2pDestroyStream      = self.p2pdll.nip2pDestroyStream
        self.nip2pLinkStream         = self.p2pdll.nip2pLinkStream
        self.nip2pEnableStream       = self.p2pdll.nip2pEnableStream
        self.nip2pDisableStream      = self.p2pdll.nip2pDisableStream
        self.nip2pUnlinkStream       = self.p2pdll.nip2pUnlinkStream
        self.nip2pWaitForStreamEvent = self.p2pdll.nip2pWaitForStreamEvent
        self.nip2pGetAttribute       = self.p2pdll.nip2pGetAttribute

def start_p2p_fifo(readerSession, readerFifoName, writerSession, writerFifoName):
    """
    Args:
        readerSession (nifpga.Session): The NIFPGA Session of the Reader FPGA
        readerFifoName (str): The Name of the Reader FIFO (sink)
        writerSession (nifpga.Session): The NIFPGA Session of the Writer FPGA
        writerFifoName (str): The Name of the Writer FIFO (source)

    Returns:
        (P2PStream): The P2PStream object
    """
    writer_endpoint = writerSession.fifos[writerFifoName].get_peer_to_peer_endpoint()
    reader_endpoint = readerSession.fifos[readerFifoName].get_peer_to_peer_endpoint()
    return P2PStream(writer_endpoint, reader_endpoint)

class P2PStream:
    def __init__(self, writerEndpointId, readerEndpointId, enable=True):
        self.p2pdll = NIP2PLibrary()
        self.streamHandle = c_uint(0)
        assertP2PSuccess(self.p2pdll.nip2pCreateAndLinkStream(writerEndpointId,
                                                                                readerEndpointId,
                                                                                c_ubyte(enable),
                                                                                byref(self.streamHandle)))

    def __enter__(self):
        return self

    def __exit__(self, err_type, err_value, err_traceback):
        self.destroy()

    def destroy(self):
        if self.streamHandle:
            assertP2PSuccess(self.p2pdll.nip2pDestroyStream(self.streamHandle))

    def link(self):
        assertP2PSuccess(self.p2pdll.nip2pLinkStream(self.streamHandle))

    def enable(self):
        assertP2PSuccess(self.p2pdll.nip2pEnableStream(self.streamHandle))

    def disable(self):
        assertP2PSuccess(self.p2pdll.nip2pDisableStream(self.streamHandle))

    def unlink(self):
        assertP2PSuccess(self.p2pdll.nip2pUnlinkStream(self.streamHandle))

    def flushAndDisable(self, timeoutMsec=250):
        flushTimedOut = c_bool(False)
        assertP2PSuccess(self.p2pdll.nip2pFlushAndDisableStream(self.streamHandle,
                                                                                  timeoutMsec,
                                                                                  byref(flushTimedOut)))
        return flushTimedOut.value

    def waitForEvent(self, event, timeoutMsec):
        assertP2PSuccess(self.p2pdll.nip2pWaitForStreamEvent(self.streamHandle,
                                                                              event,
                                                                              timeoutMsec))

    def getState(self):
        streamState = c_uint(kStreamAttributeStreamState)
        assertP2PSuccess(self.p2pdll.nip2pGetAttribute(self.streamHandle,
                                                                      0,
                                                                      byref(streamState)))
        return streamState.value

    def ensureFlushingSoon(self):
        """This method waits up to 5 seconds for the stream state to be
        'flushing'.  If it doesn't get to this state within the time
        limit, this method throws an exception.  Otherwise it returns"""
        pollHelper(lambda: self.getState() == kStreamStateFlushing,
                              totalMSToWait = 5000,
                              exceptionMsg = "Stream failed to enter the 'flushing' state")

def _createEnsureStateFn(stateName, stateCode):
    # I needed to split this code out into a helper function (rather
    # than put this code in the loop below).  This forces python to
    # create a new variable binding (w/o which this won't work).
    def ensureFn(self):
        actualState = self.getState()
        if stateCode != actualState:
            raise P2PStateException(stateCode, actualState)
    setattr(P2PStream,'ensure'+stateName, ensureFn)     
    #P2PStream.__dict__['ensure' + stateName] = ensureFn

# Create ensureXXX functions
for id, stateDict in list(nip2pStates.items()):
    _createEnsureStateFn(stateDict['short_name'], id)
