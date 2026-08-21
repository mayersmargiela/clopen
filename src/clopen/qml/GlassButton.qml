import QtQuick
import QtQuick.Controls

Button {
    id: control
    property bool darkMode: true
    property bool primary: false
    property bool danger: false
    property bool quiet: false
    property int fontSize: 13

    implicitHeight: 38
    implicitWidth: Math.max(42, contentItem.implicitWidth + 24)
    padding: 0

    contentItem: Text {
        text: control.text
        color: control.darkMode ? "#F6F7FA" : "#20242A"
        font.pixelSize: control.fontSize
        font.weight: control.primary ? Font.DemiBold : Font.Medium
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        renderType: Text.NativeRendering
        opacity: control.enabled ? 1.0 : 0.42
    }

    background: Item {
        GlassPane {
            anchors.fill: parent
            darkMode: control.darkMode
            cornerRadius: control.primary ? 13 : 11
            density: control.primary
                     ? (control.darkMode ? 0.050 : 0.105)
                     : (control.quiet ? (control.darkMode ? 0.020 : 0.060)
                                      : (control.darkMode ? 0.048 : 0.105))
            highlight: control.hovered ? 0.42 : (control.primary ? 0.34 : 0.22)
            opacity: control.enabled ? (control.pressed ? 0.80 : 1.0) : 0.52
        }

        // Primary action stays neutral glass. No fixed brand-blue fill: the
        // desktop colour should remain visible through the material.
        Rectangle {
            anchors.fill: parent
            radius: control.primary ? 13 : 11
            visible: control.primary
            color: control.danger ? Qt.rgba(0.95, 0.35, 0.39, 1.0) : Qt.rgba(1, 1, 1, 1.0)
            opacity: control.enabled
                     ? (control.danger ? (control.hovered ? 0.12 : 0.08)
                                       : (control.hovered ? 0.10 : 0.055))
                     : 0.025
        }

        Rectangle {
            visible: control.primary
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            height: 1
            color: Qt.rgba(1, 1, 1, control.hovered ? 0.52 : 0.36)
        }
    }
}
