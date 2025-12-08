//
//  DotPattern.swift
//  MagnetarStudio
//
//  Dot pattern background for workflow builder canvas
//

import SwiftUI

// MARK: - Dot Pattern Background

struct DotPattern: View {
    let gap: CGFloat = 16
    let dotSize: CGFloat = 1

    var body: some View {
        GeometryReader { geometry in
            Path { path in
                let cols = Int(geometry.size.width / gap)
                let rows = Int(geometry.size.height / gap)

                for row in 0...rows {
                    for col in 0...cols {
                        let x = CGFloat(col) * gap
                        let y = CGFloat(row) * gap
                        path.addEllipse(in: CGRect(x: x - dotSize/2, y: y - dotSize/2, width: dotSize, height: dotSize))
                    }
                }
            }
            .fill(Color.gray.opacity(0.2))
        }
    }
}
