import QtQuick

Rectangle {
    id: glass

    property bool darkMode: true
    property real density: 0.025
    property real highlight: 0.12
    property real cornerRadius: 16

    color: "transparent"
    radius: cornerRadius
    border.width: highlight > 0 ? 1 : 0
    border.color: Qt.rgba(1, 1, 1, Math.min(0.30, highlight * 0.72))
    clip: true

    // Neutral optical veil only. Environment colour still comes entirely from
    // whatever is behind the window. No black/blue/gray tint is painted here.
    gradient: Gradient {
        GradientStop { position: 0.00; color: Qt.rgba(1, 1, 1, Math.min(0.14, glass.density * 1.45)) }
        GradientStop { position: 0.22; color: Qt.rgba(1, 1, 1, Math.min(0.11, glass.density * 0.90)) }
        GradientStop { position: 0.62; color: Qt.rgba(1, 1, 1, Math.min(0.08, glass.density * 0.48)) }
        GradientStop { position: 1.00; color: Qt.rgba(1, 1, 1, Math.min(0.05, glass.density * 0.20)) }
    }

    // Inner rim gives the pane some perceived thickness without a hard outline.
    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: Math.max(0, glass.cornerRadius - 1)
        color: "transparent"
        border.width: glass.highlight > 0 ? 1 : 0
        border.color: Qt.rgba(1, 1, 1, Math.min(0.12, glass.highlight * 0.22))
    }

    // Specular top glint: strongest near the centre, kept deliberately subtle.
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: Math.max(12, glass.cornerRadius * 0.9)
        anchors.rightMargin: Math.max(12, glass.cornerRadius * 0.9)
        height: 1
        color: Qt.rgba(1, 1, 1, Math.min(0.32, glass.highlight + 0.10))
    }
}
