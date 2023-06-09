# Support class for the Jython implementation of Logix
# Copyright (c) 2022 Rangachari Anand

class JylogixListener(java.beans.PropertyChangeListener):
    def __init__(self, logixList):
        self.logix = logixList

    def getEntryExit(self, name):
        entryExitPairs = jmri.InstanceManager.getDefault(jmri.jmrit.entryexit.EntryExitPairs)
        destinations = entryExitPairs.getNamedBeanSet()
        for d in destinations:
            if d.getUserName() == name or d.getSystemName() == name:
                return d
        return None

    def attach(self):
        # We need to keep track of objects that have already had
        # listeners attached. Don't want to attach duplicate
        # listeners! We use previouslyHandled for this purpose.
        previouslyHandled = set()
        for conditional in self.logix:
            guardSet = set()
            conditional['guardSet'] = guardSet
            for (otype, oid, _) in conditional['guard']:
                if otype == 'Sensor':
                    sensor = sensors.getSensor(oid)
                    if sensor is None:
                        print('ERROR Could not locate sensor ' + oid)
                    else:
                        guardSet.add(sensor.getSystemName())
                        if (otype, oid) in previouslyHandled:
                            pass
                        else:
                            sensor.addPropertyChangeListener(self)
                            previouslyHandled.add((otype, oid))
                            #print('Attached listener to sensor ' + oid)
                elif otype == 'Turnout':
                    turnout = turnouts.getTurnout(oid)
                    if turnout is None:
                        print('ERROR Could not locate turnout ' + oid)
                    else:
                        guardSet.add(turnout.getSystemName())
                        if (otype, oid) in previouslyHandled:
                            pass
                        else:
                            turnout.addPropertyChangeListener(self)
                            previouslyHandled.add((otype, oid))
                            #print('Attached listener to turnout' + oid)
                elif otype == 'EntryExit':
                    entryExit = self.getEntryExit(oid)
                    if entryExit is None:
                        print('ERROR Could not locate entry exit ' + oid)
                    else:
                        guardSet.add(entryExit.getSystemName())
                        if (otype, oid) in previouslyHandled:
                            pass
                        else:
                            entryExit.addPropertyChangeListener(self)
                            previouslyHandled.add((otype, oid))
                            #print('Attached listener to entry exit' + oid)
                else:
                    print ('ERROR Unknown object type ' + otype)
        print('Guard sets')
        for (i, l) in enumerate(self.logix):
            guards = ' '.join(l['guardSet'])
            #print('Conditional ' + l['id'] + ' Guards:' + guards)
    
    def convertStateToString(self, state, objectType):
        if objectType == 'Turnout':
            if state == 2:
                return 'NORMAL'
            elif state == 4:
                return 'REVERSE'
            else:
                return ''
        if state == 2:
            return 'ACTIVE'
        elif state == 4:
            return 'INACTIVE'
        else:
            return ''
        
    # These states for signal heads are defined in NamedBeanBundle.properties
    # The predefined constants like RED are defined in JmriScriptEngineManager.java
    # where it is defined as SignalHead.RED
    def convertSignalHeadState(self, s):
        if s == 'Red':
            return RED
        elif s == 'Yellow':
            return YELLOW
        elif s == 'Green':
            return GREEN
        elif s == 'Lunar':
            return LUNAR
        elif s == 'Dark':
            return DARK
        elif s == 'Flashing Red':
            return FLASHRED
        elif s == 'Flashing Yellow':
            return FLASHYELLOW
        elif s == 'Flashing Green':
            return FLASHGREEN
        elif s == 'Flashing Lunar':
            return FLASHLUNAR
        else:
            return DARK

    def evaluateGuard(self, guard):
        otype = guard[0]
        oid = guard[1]
        triggerState = guard[2]
        if otype == 'Sensor':
            sensor = sensors.getSensor(oid)
            state = self.convertStateToString(sensor.getKnownState(), otype)
            #print( oid + ' ' + state + ' == ' + triggerState + '?')
            return state == triggerState
        elif otype == 'Turnout':
            turnout = turnouts.getTurnout(oid)
            state = self.convertStateToString(turnout.getKnownState(), otype)
            #print( oid + ' ' + state + ' == ' + triggerState + '?')
            return state == triggerState
        elif otype == 'EntryExit':
            entryExit = self.getEntryExit(oid)
            state = self.convertStateToString(entryExit.getState(), otype)
            #print( oid + ' ' + state + ' == ' + triggerState + '?')
            return state == triggerState
        elif otype == 'SignalMastAspect':
            signalMast = masts.getSignalMast(oid)
            #print( oid + ' ' + signalMast.getAspect() + ' == ' + triggerState + '?')
            return signalMast.getAspect() == triggerState
        return False

    def evaluateGuards(self, guards, formula):
        if len(guards) == 1:
            return self.evaluateGuard(guards[0])
        truthValues = []
        for g in guards:
            truthValues.append(str(self.evaluateGuard(g)))
        f = formula % tuple(truthValues)
        #print('Final formula: ' + f)
        value = eval(f)
        return value

    def interpretOption(self, option, evaluation):
        return (option == 'if_change') or (option == 'if_true' and evaluation) or (option == 'if_false' and not evaluation)

    def takeActions(self, actions, logixId, evaluation):
        #print '----'
        #print 'Entered takeActions. Evaluation is ', evaluation
        for (a_type, a_oid, a_state, a_option) in actions:
            #print 'Checking action', a_type, a_oid, a_state, a_option
            if a_type == 'Turnout' and self.interpretOption(a_option, evaluation):
                t = turnouts.getTurnout(a_oid)
                if t is None:
                    print('ERROR unknown turnout id ' + a_oid)
                else:
                    if a_state == 'NORMAL':
                        t.state = CLOSED
                    elif a_state == 'REVERSE':
                        t.state = THROWN
                    elif a_state == 'TOGGLE':
                        if t.state == THROWN:
                            t.state = CLOSED
                        else:
                            t.state = THROWN
                    else:
                        print('ERROR unknown turnout state ' + a_state)
                    print( 'Logix ' + logixId + ' Action set turnout ' + a_oid + ' to ' + a_state)
            elif a_type == 'Sensor' and self.interpretOption(a_option, evaluation):
                s = sensors.getSensor(a_oid)
                if s is None:
                    print('ERROR unknown sensor id' + a_oid)
                else:
                    if a_state == 'ACTIVE':
                        s.state = ACTIVE
                    elif a_state == 'INACTIVE':
                        s.state = INACTIVE
                    elif a_state == 'TOGGLE':
                        if s.state == ACTIVE:
                            s.state = INACTIVE
                        else:
                            s.state = ACTIVE
                    else:
                        print('ERROR unknown sensor state ' + a_state)
                    print( 'Logix ' + logixId + ' action set sensor ' + a_oid + ' to ' + a_state )
            elif a_type == 'SignalMast' and self.interpretOption(a_option, evaluation):
                signalMast = masts.getSignalMast(a_oid)
                if signalMast is None:
                    print('ERROR unknown signal mast ' + a_oid)
                else:
                    signalMast.setAspect(a_state)
                print('Logix ' + logixId + ' action setting signal mast ' + a_oid + ' to ' + a_state)
            elif a_type == 'Light' and self.interpretOption(a_option, evaluation):
                l = lights.getLight(a_oid)
                if l is None:
                    print('Error unknown light: ' + a_oid)
                else:
                    if a_state == 'ACTIVE':
                        l.setState(ON)
                    elif a_state == 'INACTIVE':
                        l.setState(OFF)
                    else:
                        print('ERROR Unknown light state ' + a_state)
                print( 'Logix ' + logixId + ' action set light ' + a_oid + ' to ' + a_state)
            elif a_type == 'SignalHead' and self.interpretOption(a_option, evaluation):
                signalHead = signals.getSignalHead(a_oid)
                if signalHead is None:
                    print('Error unknown signal head ' + a_oid)
                else:
                    appearance = self.convertSignalHeadState(a_state)
                    signalHead.setAppearance(appearance)
                    print( 'Logix ' + logixId + ' action set signal head ' + a_oid + ' to ' + a_state)

    # This method is required by java.beans.PropertyChangeListener
    def propertyChange(self, event):
        sname = event.getSource().getSystemName()
        #print('Event source: ' + sname + ' New value ' + str(event.getNewValue()))
        for l in self.logix:
            if sname in l['guardSet']:
                #print('Event was captured by logix ' + l['id'])
                # Now evaluate the actual conditions
                evaluation = self.evaluateGuards(l['guard'], l['formula'])
                #print('Evaluated to: ' + str(evaluation))
                self.takeActions(l['action'], l['id'], evaluation)
            else:
                #print('Event not captured by logix ' + str(i))
                pass

    # Evaluate all Logix when starting up
    def handleStartup(self):
        for l in self.logix:
            evaluation = self.evaluateGuards(l['guard'], l['formula'])
            print('Logix startup ' + l['id'] + ' evaluated to: ' + str(evaluation))
            self.takeActions(l['action'], l['id'], evaluation)
